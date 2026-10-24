"""
modelos.py - Clases de dominio (Programación II - POO)

Clases:
    Estudiante        -> representa a un estudiante (atributos privados + validaciones)
    ListaEstudiantes  -> lógica de negocio: agregar, editar, eliminar y buscar
"""
import re

# Expresión regular simple para validar emails (algo@dominio.ext)
_PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Estudiante:
    """Un estudiante con nombre, apellido y email.

    Los atributos son privados (encapsulación) y se acceden mediante
    propiedades que validan el dato; si es inválido lanzan ValueError.
    """

    def __init__(self, nombre, apellido, email, id=None):
        self.__id = id
        self.nombre = nombre      # pasa por el setter (valida)
        self.apellido = apellido
        self.email = email

    # ---- id (lo asigna la base de datos) ----
    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, valor):
        self.__id = valor

    # ---- nombre ----
    @property
    def nombre(self):
        return self.__nombre

    @nombre.setter
    def nombre(self, valor):
        valor = (valor or "").strip()
        if len(valor) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres.")
        self.__nombre = valor.title()

    # ---- apellido ----
    @property
    def apellido(self):
        return self.__apellido

    @apellido.setter
    def apellido(self, valor):
        valor = (valor or "").strip()
        if len(valor) < 2:
            raise ValueError("El apellido debe tener al menos 2 caracteres.")
        self.__apellido = valor.title()

    # ---- email ----
    @property
    def email(self):
        return self.__email

    @email.setter
    def email(self, valor):
        valor = (valor or "").strip().lower()
        if not _PATRON_EMAIL.match(valor):
            raise ValueError("El email no tiene un formato válido.")
        self.__email = valor

    @property
    def nombre_completo(self):
        return f"{self.__nombre} {self.__apellido}"

    # ---- conversión a/desde documento de MongoDB ----
    def a_diccionario(self):
        """Documento que se guarda en la colección (sin _id)."""
        return {"nombre": self.__nombre, "apellido": self.__apellido,
                "email": self.__email}

    @classmethod
    def desde_diccionario(cls, doc):
        """Crea un Estudiante a partir de un documento de MongoDB."""
        return cls(doc["nombre"], doc["apellido"], doc["email"],
                   id=str(doc["_id"]))


class ListaEstudiantes:
    """Gestiona los estudiantes. Delega el guardado en un repositorio."""

    def __init__(self, repositorio):
        self.__repositorio = repositorio

    def agregar(self, nombre, apellido, email):
        """Valida y guarda un estudiante nuevo. Devuelve el Estudiante."""
        estudiante = Estudiante(nombre, apellido, email)  # valida
        estudiante.id = self.__repositorio.guardar(estudiante)
        return estudiante

    def editar(self, id, nombre, apellido, email):
        """Modifica un estudiante existente."""
        estudiante = self.obtener(id)
        if estudiante is None:
            raise LookupError("El estudiante no existe.")
        estudiante.nombre = nombre
        estudiante.apellido = apellido
        estudiante.email = email
        self.__repositorio.actualizar(estudiante)
        return estudiante

    def eliminar(self, id):
        """Elimina un estudiante. Devuelve True si existía."""
        return self.__repositorio.eliminar(id)

    def obtener(self, id):
        return self.__repositorio.obtener(id)

    def obtener_todos(self):
        return self.__repositorio.cargar()

    def buscar_por_nombre(self, texto):
        """Devuelve los estudiantes cuyo nombre o apellido coincide con el texto."""
        texto = (texto or "").strip()
        return self.__repositorio.cargar(texto) if texto else self.obtener_todos()

    def contar(self):
        return len(self.obtener_todos())
