# Instalación y uso

1. Instalar Python 3.10+ y crear una base de datos en MongoDB Atlas (o instalar MongoDB local).
2. En CMD, entrar a la carpeta `registro_estudiantes` y ejecutar:
   ```bat
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Configurar `MONGO_URI` y `MONGO_BD` en `.env`. La aplicación carga este archivo al iniciar y guarda todos los datos en las colecciones de MongoDB. Reemplazá usuario, contraseña y host con los datos de Atlas. En la URI, codificá los caracteres reservados para URL: por ejemplo, `@` se escribe `%40` y `ñ` se escribe `%C3%B1`. No compartas ni subas `.env`; ya está excluido por `.gitignore`.
4. Ejecutar `python app.py` y abrir `http://127.0.0.1:5000`.
5. Los alumnos crean una cuenta en **Crear cuenta de alumno** con nombre, apellido, email y contraseña (mínimo 8 caracteres). Para entrar luego usan su nombre y contraseña. Toda cuenta registrada obtiene rol `alumno`; no puede autoconvertirse en administrador.
6. Para habilitar una cuenta de administrador, asigná `rol: "admin"` al documento correspondiente en la colección `usuarios`. El programa no crea usuarios ni datos de ejemplo al iniciar.

## Conectar con MongoDB Atlas en PowerShell sin archivo `.env`
En una misma ventana de PowerShell, desde la carpeta del proyecto:
```powershell
$env:MONGO_URI = 'mongodb+srv://USUARIO:CONTRASEÑA_CODIFICADA@CLUSTER.mongodb.net/?retryWrites=true&w=majority'
$env:MONGO_BD = 'registro_alumnos'
$env:SECRET_KEY = 'una-clave-larga-y-aleatoria'
.\venv\Scripts\python.exe app.py
```
La app verifica la conexión con un `ping` al iniciar y distingue una URI mal formada, errores de autenticación y problemas de red. Si la URI no es válida, codificá para URL los caracteres especiales del usuario o la contraseña (por ejemplo, `@` como `%40` y `ñ` como `%C3%B1`). Si Atlas rechaza la autenticación, confirmá que el usuario y la contraseña sean los de **Database Access**, no los de la cuenta web de Atlas.

## Seguridad
- Las contraseñas se guardan usando hashes seguros, no en texto plano.
- Las rutas administrativas verifican el rol en el servidor.
- Configurá `SECRET_KEY` y protegé las credenciales de las cuentas guardadas en MongoDB antes de publicar la app en internet.
- Para un despliegue real, añadí HTTPS, protección CSRF y un flujo seguro de recuperación de contraseña.
