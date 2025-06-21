# 💱 EasyChange

**EasyChange** es una plataforma de intercambio de monedas construida con una arquitectura de microservicios sobre AWS usando una infraestructura **serverless**. Permite a los usuarios crear cuentas, gestionar monedas, realizar conversiones con tasas de cambio en tiempo real y visualizar su historial de transacciones.

## 🚀 Funcionalidades Principales

- Registro y autenticación de usuarios mediante JWT.
- Gestión de cuentas bancarias por usuario.
- Conversión de monedas en tiempo real (Soles ↔ Dólares).
- Consulta de tasas de cambio usando [exchangerate.host](https://exchangerate.host/).
- Configuración de alertas de tipo de cambio.
- Historial de operaciones por usuario.
- Panel administrativo para definir límites y franjas horarias.

## 🛠️ Tecnologías Utilizadas

- **AWS Lambda** – Lógica de microservicios.
- **Amazon API Gateway** – Gestión de endpoints REST.
- **Amazon DynamoDB** – Base de datos NoSQL para persistencia.
- **Serverless Framework** – Despliegue y organización de servicios.
- **Python 3.9** – Lenguaje backend.
- **Postman** – Pruebas y documentación de endpoints.

## 🧱 Arquitectura

EasyChange está compuesto por los siguientes microservicios:

- `auth` – Registro, login y gestión de usuarios.
- `profile` – Manejo de cuentas bancarias y alertas.
- `currency` – Transferencias, conversiones y reportes.
- `exchange` – Consulta y persistencia de tasas de cambio en tiempo real.
- `admin` – Gestión de configuración del sistema.

> Cada microservicio es independiente, desplegado mediante Serverless Framework, y sigue patrones como **Singleton** (para acceso compartido a recursos como DynamoDB) y **Facade** (mediante API Gateway como punto de entrada único).

## 📁 Estructura del Proyecto

easychange/
├── user/
├── profile/
├── currency/
├── exchange/
├── admin/
├── README.md


## 📬 Colecciones Postman - Cambio de Monedas

Puedes importar estas colecciones en [Postman](https://www.postman.com/) para probar los endpoints desarrollados en el proyecto. Las colecciones están en la carpeta `backend/postman_requests/`.

### 🔗 Archivos disponibles:

- [ADMIN.postman_collection.json]
- [Currency.postman_collection.json]
- [EXCHANGE.postman_collection.json]
- [Profile.postman_collection.json]
- [User.postman_collection.json]

## ⚙️ Configuración

Este proyecto requiere que tengas configuradas las siguientes variables de entorno (env vars) por cada microservicio:

```env
SLS_ORG (Serverless Org)
AWS_ROLE_ARN (Rol de AWS)
```

## 🧪 Pruebas
Cada función Lambda ha sido probada individualmente mediante Postman. También se han realizado pruebas de integración para verificar el flujo entre servicios.

## 🧠 Patrones de Diseño Usados
Singleton: Gestión única de recursos como boto3.resource y boto3.client.

Facade: Uso de API Gateway para exponer una interfaz uniforme.

Adapter (en progreso): Posibilidad de conmutar entre dos APIs externas de tipo de cambio.

## 📄 Licencia
Este proyecto es parte del curso de Arquitectura y Desarrollo de Software en UTEC.
Licencia de uso académico.
