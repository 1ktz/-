"""
repositorio.py - Acceso a datos (capa que conecta con MongoDB Atlas)

La conexión se lee del secret de Codespaces MONGODB (variable de entorno).
Los usuarios iniciales se crean desde los secrets:
    ADMIN_USUARIO, ADMIN_PASSWORD, USUARIO_NOMBRE, USUARIO_PASSWORD

CONTRATO que debe cumplir cualquier repositorio de estudiantes (lo usa ListaEstudiantes):
    guardar(estudiante)   -> id (str) del nuevo documento
    cargar(texto=None)    -> lista de Estudiante (filtrada por nombre/apellido si hay texto)
    obtener(id)           -> Estudiante o None
    actualizar(estudiante)-> None
    eliminar(id)          -> bool

Colecciones:
    estudiantes -> {_id, nombre, apellido, email}
    usuarios    -> {_id, usuario, password (hash), rol}
"""
import os
import re
import uuid

from modelos import Estudiante

NOMBRE_BD = "registro_alumnos"


def _obtener_uri():
    """Lee la cadena de conexión desde el secret MONGODB (o usa localhost)."""
    return os.environ.get("MONGODB", "mongodb://localhost:27017")


def _obtener_bd(uri=None, nombre_bd=NOMBRE_BD):
    from pymongo import MongoClient  # import aquí para poder correr sin pymongo
    cliente = MongoClient(uri or _obtener_uri(), serverSelectionTimeoutMS=5000)
    return cliente[nombre_bd]


class RepositorioEstudiantes:
    """Repositorio real: guarda estudiantes en MongoDB usando PyMongo."""

    def __init__(self, uri=None, nombre_bd=NOMBRE_BD):
        self.__coleccion = _obtener_bd(uri, nombre_bd)["estudiantes"]

    @staticmethod
    def __a_object_id(id):
        from bson import ObjectId
        from bson.errors import InvalidId
        try:
            return ObjectId(id)
        except (InvalidId, TypeError):
            return None

    def guardar(self, estudiante):
        resultado = self.__coleccion.insert_one(estudiante.a_diccionario())
        return str(resultado.inserted_id)

    def cargar(self, texto=None):
        filtro = {}
        if texto:
            patron = {"$regex": re.escape(texto), "$options": "i"}  # sin distinguir mayúsculas
            filtro = {"$or": [{"nombre": patron}, {"apellido": patron}]}
        docs = self.__coleccion.find(filtro).sort([("apellido", 1), ("nombre", 1)])
        return [Estudiante.desde_diccionario(d) for d in docs]

    def obtener(self, id):
        oid = self.__a_object_id(id)
        doc = self.__coleccion.find_one({"_id": oid}) if oid else None
        return Estudiante.desde_diccionario(doc) if doc else None

    def actualizar(self, estudiante):
        oid = self.__a_object_id(estudiante.id)
        self.__coleccion.update_one({"_id": oid}, {"$set": estudiante.a_diccionario()})

    def eliminar(self, id):
        oid = self.__a_object_id(id)
        return bool(oid) and self.__coleccion.delete_one({"_id": oid}).deleted_count == 1


class RepositorioUsuarios:
    """Usuarios del sistema (admin / usuario). Las contraseñas se guardan hasheadas."""

    def __init__(self, uri=None, nombre_bd=NOMBRE_BD):
        self.__coleccion = _obtener_bd(uri, nombre_bd)["usuarios"]
        self.__coleccion.create_index("usuario", unique=True)

    def crear_iniciales(self):
        """Crea el admin y el usuario común desde los secrets, si todavía no existen."""
        from werkzeug.security import generate_password_hash
        iniciales = [
            (os.environ.get("ADMIN_USUARIO"), os.environ.get("ADMIN_PASSWORD"), "admin"),
            (os.environ.get("USUARIO_NOMBRE"), os.environ.get("USUARIO_PASSWORD"), "usuario"),
        ]
        for nombre, clave, rol in iniciales:
            if nombre and clave and not self.__coleccion.find_one({"usuario": nombre}):
                self.__coleccion.insert_one({
                    "usuario": nombre,
                    "password": generate_password_hash(clave),
                    "rol": rol,
                })

    def verificar(self, usuario, clave):
        """Devuelve {'usuario', 'rol'} si las credenciales son correctas, si no None."""
        from werkzeug.security import check_password_hash
        doc = self.__coleccion.find_one({"usuario": usuario})
        if doc and check_password_hash(doc["password"], clave):
            return {"usuario": doc["usuario"], "rol": doc["rol"]}
        return None


class RepositorioMemoria:
    """Repositorio temporal en memoria (se pierde al cerrar).
    Sirve para probar la interfaz mientras la base en MongoDB no está lista."""

    def __init__(self):
        self.__datos = {}

    def guardar(self, estudiante):
        id_nuevo = uuid.uuid4().hex
        self.__datos[id_nuevo] = estudiante.a_diccionario()
        return id_nuevo

    def cargar(self, texto=None):
        texto = (texto or "").lower()
        salida = []
        for id_, d in self.__datos.items():
            if not texto or texto in d["nombre"].lower() or texto in d["apellido"].lower():
                salida.append(Estudiante.desde_diccionario({**d, "_id": id_}))
        return sorted(salida, key=lambda e: (e.apellido, e.nombre))

    def obtener(self, id):
        d = self.__datos.get(id)
        return Estudiante.desde_diccionario({**d, "_id": id}) if d else None

    def actualizar(self, estudiante):
        self.__datos[estudiante.id] = estudiante.a_diccionario()

    def eliminar(self, id):
        return self.__datos.pop(id, None) is not None
