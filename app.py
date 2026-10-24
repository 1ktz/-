"""Sistema escolar Flask: autenticación y permisos por rol."""
import os
from functools import wraps
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from modelos import ListaEstudiantes
from repositorio import RepositorioEstudiantes, RepositorioMemoria

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cambiar-esta-clave-secreta-antes-de-publicar')
USAR_MEMORIA = os.environ.get('USAR_MEMORIA') == '1'
if USAR_MEMORIA:
    repositorio = RepositorioMemoria()
    usuarios, notas, inasistencias = {}, {}, {}
else:
    from pymongo import MongoClient
    cliente = MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017'), serverSelectionTimeoutMS=3000)
    bd = cliente[os.environ.get('MONGO_BD', 'registro_alumnos')]
    repositorio = RepositorioEstudiantes(os.environ.get('MONGO_URI', 'mongodb://localhost:27017'), os.environ.get('MONGO_BD', 'registro_alumnos'))
    usuarios, notas, inasistencias = bd['usuarios'], bd['notas'], bd['inasistencias']
lista = ListaEstudiantes(repositorio)
MATERIAS = ['Matemáticas', 'Lengua', 'Inglés', 'Química', 'Informática', 'Física', 'Historia']

# Crear administrador inicial una sola vez. Cambiar estas variables antes de publicar.
def buscar_usuario(nombre):
    if USAR_MEMORIA:
        return next((u for u in usuarios.values() if u['nombre_usuario'].casefold() == nombre.casefold()), None)
    return usuarios.find_one({'nombre_usuario': nombre}) or usuarios.find_one({'nombre_usuario': {'$regex': '^' + __import__('re').escape(nombre) + '$', '$options': 'i'}})

def guardar_usuario(doc):
    if USAR_MEMORIA:
        usuarios[doc['nombre_usuario'].lower()] = doc
    else:
        usuarios.insert_one(doc)

def todos_de(coleccion, filtro=None):
    if USAR_MEMORIA:
        return [dict(v) for v in coleccion.values() if all(v.get(k) == val for k, val in (filtro or {}).items() )]
    return list(coleccion.find(filtro or {}, {'_id': 0}))

def guardar_registro(coleccion, clave, doc):
    if USAR_MEMORIA:
        coleccion[doc[clave]] = dict(doc)
    else:
        coleccion.replace_one({clave: doc[clave]}, doc, upsert=True)

def borrar_registro(coleccion, clave, valor):
    if USAR_MEMORIA:
        return coleccion.pop(valor, None) is not None
    return coleccion.delete_one({clave: valor}).deleted_count > 0

admin_name = os.environ.get('ADMIN_USER', 'admin')
admin_password = os.environ.get('ADMIN_PASSWORD', 'Cambiar123!')
if not buscar_usuario(admin_name):
    guardar_usuario({'nombre_usuario': admin_name, 'nombre': 'Administrador', 'apellido': 'Sistema', 'email': 'admin@escuela.local', 'password_hash': generate_password_hash(admin_password), 'rol': 'admin'})


def login_requerido(f):
    @wraps(f)
    def envoltura(*args, **kwargs):
        if 'usuario' not in session:
            flash('Iniciá sesión para continuar.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return envoltura

def admin_requerido(f):
    @wraps(f)
    def envoltura(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        if session.get('rol') != 'admin':
            abort(403, description='No tenés permisos de administrador para realizar esta acción.')
        return f(*args, **kwargs)
    return envoltura

def usuario_actual():
    return buscar_usuario(session.get('usuario', ''))

@app.errorhandler(Exception)
def error_general(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return render_template('error.html', mensaje=e.description), e.code
    app.logger.exception(e)
    return render_template('error.html', mensaje='No se pudo completar la operación. Verificá que MongoDB esté funcionando.'), 500

@app.route('/')
def inicio():
    if 'usuario' in session:
        return redirect(url_for('panel_admin' if session.get('rol') == 'admin' else 'panel_alumno'))
    return render_template('inicio.html', total=lista.contar())

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if len(nombre) < 2 or len(apellido) < 2 or '@' not in email or len(password) < 8:
            flash('Completá todos los campos. La contraseña debe tener al menos 8 caracteres.', 'error')
        elif buscar_usuario(nombre):
            flash('Ese nombre ya está registrado. Elegí otro nombre de usuario.', 'error')
        elif not USAR_MEMORIA and usuarios.find_one({'email': email}):
            flash('Ya existe una cuenta con ese email.', 'error')
        elif USAR_MEMORIA and any(u['email'] == email for u in usuarios.values()):
            flash('Ya existe una cuenta con ese email.', 'error')
        else:
            guardar_usuario({'nombre_usuario': nombre, 'nombre': nombre.title(), 'apellido': apellido.title(), 'email': email, 'password_hash': generate_password_hash(password), 'rol': 'alumno'})
            flash('Cuenta creada. Ahora podés iniciar sesión con tu nombre y contraseña.', 'ok')
            return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre = request.form.get('nombre_usuario', '').strip()
        password = request.form.get('password', '')
        u = buscar_usuario(nombre)
        if u and check_password_hash(u['password_hash'], password):
            session.clear(); session['usuario'] = u['nombre_usuario']; session['rol'] = u['rol']
            flash('¡Bienvenido/a!', 'ok')
            return redirect(url_for('panel_admin' if u['rol'] == 'admin' else 'panel_alumno'))
        flash('Nombre de usuario o contraseña incorrectos.', 'error')
    return render_template('login.html')

@app.route('/salir', methods=['POST'])
def salir():
    session.clear(); flash('Sesión cerrada.', 'ok'); return redirect(url_for('inicio'))

@app.route('/alumno')
@login_requerido
def panel_alumno():
    if session.get('rol') == 'admin': return redirect(url_for('panel_admin'))
    u = usuario_actual()
    filtro = {'alumno': u['nombre_usuario']}
    return render_template('panel_alumno.html', usuario=u, materias=MATERIAS, notas=todos_de(notas, filtro), inasistencias=todos_de(inasistencias, filtro))

@app.route('/admin')
@admin_requerido
def panel_admin():
    return render_template('panel_admin.html', estudiantes=lista.obtener_todos(), usuarios=todos_de(usuarios), notas=todos_de(notas), inasistencias=todos_de(inasistencias), materias=MATERIAS)

@app.route('/admin/notas', methods=['POST'])
@admin_requerido
def admin_nota():
    alumno = request.form.get('alumno', '').strip(); materia = request.form.get('materia', ''); valor = request.form.get('valor', '').strip()
    if not buscar_usuario(alumno) or materia not in MATERIAS:
        flash('Alumno o materia inválidos.', 'error')
    else:
        try:
            nota = float(valor)
            if not 1 <= nota <= 10: raise ValueError
            clave = alumno + '|' + materia
            guardar_registro(notas, 'clave', {'clave': clave, 'alumno': alumno, 'materia': materia, 'valor': nota, 'actualizado': datetime.now().isoformat(timespec='minutes')})
            flash('Nota guardada.', 'ok')
        except ValueError: flash('La nota debe ser un número entre 1 y 10.', 'error')
    return redirect(url_for('panel_admin'))

@app.route('/admin/notas/<path:clave>/eliminar', methods=['POST'])
@admin_requerido
def admin_borrar_nota(clave):
    borrar_registro(notas, 'clave', clave); flash('Nota eliminada.', 'ok'); return redirect(url_for('panel_admin'))

@app.route('/admin/inasistencias', methods=['POST'])
@admin_requerido
def admin_inasistencia():
    alumno = request.form.get('alumno', '').strip(); fecha = request.form.get('fecha', '').strip(); cantidad = request.form.get('cantidad', '1').strip(); motivo = request.form.get('motivo', '').strip()
    if not buscar_usuario(alumno) or not fecha:
        flash('Seleccioná un alumno y una fecha válida.', 'error')
    else:
        try:
            n = int(cantidad)
            if n < 1 or n > 20: raise ValueError
            clave = alumno + '|' + fecha
            guardar_registro(inasistencias, 'clave', {'clave': clave, 'alumno': alumno, 'fecha': fecha, 'cantidad': n, 'motivo': motivo})
            flash('Inasistencia guardada.', 'ok')
        except ValueError: flash('La cantidad debe ser un número entre 1 y 20.', 'error')
    return redirect(url_for('panel_admin'))

@app.route('/admin/inasistencias/<path:clave>/eliminar', methods=['POST'])
@admin_requerido
def admin_borrar_inasistencia(clave):
    borrar_registro(inasistencias, 'clave', clave); flash('Inasistencia eliminada.', 'ok'); return redirect(url_for('panel_admin'))

# Gestión de estudiantes existente: ahora exclusiva del administrador.
def _datos_form():
    f = request.form
    return f.get('nombre', ''), f.get('apellido', ''), f.get('email', '')

@app.route('/estudiantes')
@admin_requerido
def listar():
    q = request.args.get('q', '')
    return render_template('lista.html', estudiantes=lista.buscar_por_nombre(q), q=q)

@app.route('/estudiantes/nuevo', methods=['GET', 'POST'])
@admin_requerido
def nuevo():
    if request.method == 'POST':
        try:
            e = lista.agregar(*_datos_form()); flash(f'{e.nombre_completo} fue agregado correctamente.', 'ok'); return redirect(url_for('listar'))
        except ValueError as err:
            flash(str(err), 'error'); return render_template('formulario.html', titulo='Nuevo estudiante', datos=request.form)
    return render_template('formulario.html', titulo='Nuevo estudiante', datos={})

@app.route('/estudiantes/<id>')
@admin_requerido
def detalle(id):
    estudiante = lista.obtener(id)
    if estudiante is None: flash('El estudiante no existe.', 'error'); return redirect(url_for('listar'))
    return render_template('detalle.html', e=estudiante)

@app.route('/estudiantes/<id>/editar', methods=['GET', 'POST'])
@admin_requerido
def editar(id):
    estudiante = lista.obtener(id)
    if estudiante is None: flash('El estudiante no existe.', 'error'); return redirect(url_for('listar'))
    if request.method == 'POST':
        try: lista.editar(id, *_datos_form()); flash('Datos actualizados.', 'ok'); return redirect(url_for('detalle', id=id))
        except ValueError as err: flash(str(err), 'error'); return render_template('formulario.html', titulo='Editar estudiante', datos=request.form)
    return render_template('formulario.html', titulo='Editar estudiante', datos={'nombre': estudiante.nombre, 'apellido': estudiante.apellido, 'email': estudiante.email})

@app.route('/estudiantes/<id>/eliminar', methods=['POST'])
@admin_requerido
def eliminar(id):
    flash('Estudiante eliminado.' if lista.eliminar(id) else 'No se encontró el estudiante.', 'ok'); return redirect(url_for('listar'))

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
