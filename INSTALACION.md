# Instalación y uso

1. Instalar Python 3.10+ y MongoDB (local o MongoDB Atlas).
2. En CMD, entrar a la carpeta `registro_estudiantes` y ejecutar:
   ```bat
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Configurar las variables de entorno antes de ejecutar (recomendado):
   ```bat
   set SECRET_KEY=una-clave-larga-y-aleatoria
   set ADMIN_USER=admin
   set ADMIN_PASSWORD=UnaClaveAdminSegura123!
   ```
   Si no se configuran, el administrador inicial es `admin` con contraseña `Cambiar123!`. **Cambiala antes de usar el sistema de verdad.**
4. Ejecutar `python app.py` y abrir `http://127.0.0.1:5000`.
5. Los alumnos crean una cuenta en **Crear cuenta de alumno** con nombre, apellido, email y contraseña (mínimo 8 caracteres). Para entrar luego usan su nombre y contraseña. Toda cuenta registrada obtiene rol `alumno`; no puede autoconvertirse en administrador.
6. El administrador inicia sesión con las credenciales configuradas. Puede gestionar estudiantes, notas e inasistencias desde el panel.

## Probar sin MongoDB
En CMD:
```bat
set USAR_MEMORIA=1
set ADMIN_USER=admin
set ADMIN_PASSWORD=UnaClaveAdminSegura123!
python app.py
```
En modo memoria, las cuentas y los datos se pierden al cerrar la aplicación. Para uso persistente, ejecutar con MongoDB y sin `USAR_MEMORIA=1`.

## Seguridad
- Las contraseñas se guardan usando hashes seguros, no en texto plano.
- Las rutas administrativas verifican el rol en el servidor.
- Configurá `SECRET_KEY` y una contraseña de administrador fuerte antes de publicar la app en internet.
- Para un despliegue real, añadí HTTPS, protección CSRF y un flujo seguro de recuperación de contraseña.
