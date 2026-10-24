"""
repositorio.py - Acceso a datos (capa que conecta con MongoDB)

CONTRATO que debe cumplir cualquier repositorio (lo usa ListaEstudiantes):
    guardar(estudiante)   -> id (str) del nuevo documento
    cargar(texto=None)    -> lista de Estudiante (filtrada por nombre/apellido si hay texto)
    obtener(id)           -> Estudiante o None
    actualizar(estudiante)-> None
    eliminar(id)          -> bool

Colección: estudiantes   Documento: {_id, nombre, apellido, email}
Quien diseñe la BD solo tiene que ajustar esta clase si cambia el modelo.
"""
import re
import uuid

from modelos import Estudiante


class RepositorioEstudiantes:
    """Repositorio real: guarda en MongoDB usando PyMongo."""

    def __init__(self, uri="mongodb://localhost:27017", nombre_bd="registro_alumnos"):
        from pymongo import MongoClient  # import aquí para poder correr sin pymongo
        self.__cliente = MongoClient(uri, serverSelectionTimeoutMS=3000)
        self.__coleccion = self.__cliente[nombre_bd]["estudiantes"]

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
