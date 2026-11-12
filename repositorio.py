"""
repositorio.py - Acceso a datos (capa que conecta con MongoDB Atlas)

CONTRATO que debe cumplir cualquier repositorio de estudiantes (lo usa ListaEstudiantes):
    guardar(estudiante)   -> id (str) del nuevo documento
    cargar(texto=None)    -> lista de Estudiante (filtrada por nombre/apellido si hay texto)
    obtener(id)           -> Estudiante o None
    actualizar(estudiante)-> None
    eliminar(id)          -> bool

Colecciones:
    estudiantes -> {_id, nombre, apellido, email}
    usuarios    -> {_id, nombre_usuario, nombre, apellido, email, password_hash, rol}
    notas       -> {clave, alumno, materia, valor, actualizado}
    inasistencias -> {clave, alumno, fecha, cantidad, motivo}
"""
import os
import re

from modelos import Estudiante

NOMBRE_BD = "registro_alumnos"


def _obtener_uri():
    """Obtiene la URI de MongoDB configurada por el proceso."""
    uri = os.environ.get("MONGO_URI", "").strip()
    if not uri:
        raise RuntimeError("Falta MONGO_URI para conectar el repositorio con MongoDB.")
    return uri


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


