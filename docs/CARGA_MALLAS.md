# Carga de mallas curriculares UNES

## Desde el centro de control

1. Inicia sesión con una cuenta superadministradora.
2. Abre **Administración → Cargar mallas curriculares**.
3. Selecciona el libro `.xlsx` y pulsa **Importar mallas**.
4. Revisa el resumen por hoja y abre el catálogo de unidades curriculares.

La pantalla acepta libros de hasta 5 MB. El libro se procesa en memoria y no se almacena en el servidor.

## Desde la línea de comandos

Instala dependencias y ejecuta:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_mallas "/ruta/CUADRO MALLAS PNF CON UA Y UE.xlsx"
```

## Comportamiento

- La importación es idempotente: identifica cada registro por programa, código generado u original y versión de malla; volver a cargar el libro actualiza los mismos registros.
- Las versiones POLICIAL VIEJA y POLICIAL NUEVA se conservan separadas.
- INVESTIGACIÓN PENAL y CRIMINALÍSTICA conservan sus versiones anteriores; la hoja IP Y CRIM NUEVA se vincula a ambos programas.
- Las hojas sin una etiqueta explícita de versión se registran como UNICA. PCAD se conserva como ANTERIOR porque el propio libro la identifica como malla en revisión.
- Se preservan horas, prelaciones, unidades acreditables/electivas y la fila original en el campo `datos_malla`.
- La importación crea unidades curriculares, no docentes ni aulas. Estas se asignan desde la administración después de revisar el catálogo.

## Libro recibido

El libro contiene diez hojas. El analizador reconoce las diez y prevé 571 filas curriculares antes de duplicar la hoja compartida IP Y CRIM NUEVA para sus dos programas (627 asociaciones programa-unidad). El total definitivo se muestra al finalizar la carga; las filas de total, encabezados y títulos no se importan.
