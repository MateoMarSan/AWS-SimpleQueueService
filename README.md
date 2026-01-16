\# Arquitectura como Código en AWS con Textract y GitHub Actions



\## Descripción general



En esta práctica se implementa una arquitectura \*\*serverless en AWS\*\* siguiendo el enfoque de \*\*Infraestructura como Código (IaC)\*\* mediante \*\*AWS CloudFormation\*\*, y se integra un flujo de \*\*CI/CD\*\* utilizando \*\*GitHub Actions\*\*.



El objetivo es automatizar el procesamiento de documentos subidos a Amazon S3, extraer su contenido textual mediante Amazon Textract y almacenar los resultados tanto en Amazon S3 como en Amazon DynamoDB.



Toda la infraestructura se define de forma declarativa y se despliega automáticamente en AWS cada vez que se realizan cambios en el repositorio.



---



\## Arquitectura implementada



La arquitectura sigue el siguiente flujo:



1\. Un fichero (imagen o documento) se sube a un \*\*bucket S3 de entrada\*\*.

2\. El evento de creación del objeto genera un mensaje en una \*\*cola Amazon SQS\*\*.

3\. Una \*\*función AWS Lambda\*\* es activada por la cola SQS.

4\. La función Lambda procesa el fichero utilizando \*\*Amazon Textract\*\* para extraer el texto.

5\. El resultado del procesamiento se almacena:

&nbsp;  - En un \*\*bucket S3 de salida\*\*, en formato texto o JSON.

&nbsp;  - En una \*\*tabla DynamoDB\*\*, junto con metadatos del documento.



Este enfoque desacopla los componentes, mejora la escalabilidad y permite la gestión de errores mediante reintentos automáticos.



---



\## Infraestructura como Código (IaC)



Toda la infraestructura se define en un único archivo de \*\*AWS CloudFormation\*\*, incluyendo:



\- Buckets S3 (origen y destino)

\- Cola SQS

\- Función Lambda

\- Tabla DynamoDB

\- Roles y políticas IAM necesarias

\- Asociación de eventos entre servicios



Gracias a CloudFormation, la infraestructura es:

\- Reproducible

\- Versionable

\- Automatizable

\- Fácilmente mantenible



---



\## Integración CI/CD con GitHub Actions



El proyecto incorpora \*\*GitHub Actions\*\* para automatizar el despliegue de la infraestructura en AWS.



\### Funcionamiento del pipeline



\- Cada vez que se realiza un `push` a la rama principal del repositorio:

&nbsp; 1. GitHub Actions ejecuta un workflow definido en YAML.

&nbsp; 2. El workflow se autentica contra AWS mediante credenciales seguras.

&nbsp; 3. Se ejecuta el comando `aws cloudformation deploy`.

&nbsp; 4. AWS crea o actualiza el stack según los cambios detectados.



Este proceso garantiza que la infraestructura en AWS esté siempre sincronizada con el código del repositorio.



---

