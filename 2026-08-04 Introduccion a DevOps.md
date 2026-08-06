## tags: [devops, docker, kubernetes, cicd, calms]

# DevOps — Notas de clase

## 1. Historia del desarrollo de software

### Waterfall

Flujo lineal y secuencial: `Design → Code → Test → Deploy`

### Agile

Flujo iterativo, se repiten ciclos de diseño/código/test antes de llegar al deploy: `Design → (Code → Test → Code → Test → ...) → Deploy`

### Agile con CI/CD

El deploy deja de ser un evento único al final y pasa a integrarse dentro del ciclo: `Design → Iteración → Deploy → etc.`

> [!question] ¿Por qué Agile + CD acorta la brecha y disminuye los errores? Porque se acorta el tiempo entre que se escribe el código y se lo lleva a producción. Al integrar y desplegar de forma continua, los cambios son más pequeños y frecuentes, lo que hace más fácil detectar errores rápido (feedback temprano) en lugar de acumular grandes lotes de cambios que son más difíciles de debuggear y más riesgosos de desplegar.

### Otras ventajas comunes de Agile + CD

- Releases más rápidos y frecuentes.
- Feedback más temprano de usuarios/stakeholders.
- Menor riesgo por deploy (cambios más chicos y acotados).
- Mayor capacidad de adaptación a cambios de requerimientos.
- Mejora la colaboración entre equipos (dev, QA, infra).
- Mayor calidad del producto por testing continuo.

---

## 2. Principios CALMS

Marco de referencia para entender y evaluar la cultura DevOps de una organización. Sirve para identificar qué tan "DevOps" es realmente una organización, más allá de las herramientas que use.

### C — Culture (Cultura)

DevOps no es un rol aislado, sino una mentalidad que engloba a toda la organización: desarrollo, testing e infraestructura trabajando de forma conjunta, no en silos.

### A — Automation (Automatización)

Suprime el trabajo repetitivo. Está bien vista porque reduce el error humano y libera tiempo del equipo para tareas de mayor valor.

### L — Lean

(Mencionado como parte del framework; asociado a minimizar desperdicio y optimizar el flujo de trabajo.)

### M — Measurement (Medición)

Lo que no se mide, no se puede mejorar.

- No alcanza con automatizar: en el ciclo de vida del desarrollo hay que **medir** el impacto de lo que se hizo (tiempo, costos, etc.) para la organización.
- Hay que sopesar lo manual contra lo automático.
- Se usan las **métricas DORA** como referencia estándar.
- Que algo se _pueda_ medir no significa que _todo_ se _deba_ medir.

### S — Sharing (Compartir)

Compartir cualquier hallazgo o beneficio descubierto con el resto del equipo. La idea es no quedarse individualmente con los descubrimientos, sino difundirlos.

### Beneficios de CALMS

- Releases más rápidos y confiables.
- Reducción de errores en producción.
- Ambiente colaborativo que se traduce en mayor productividad.

### Desafíos de CALMS

- Cambio cultural (el más difícil de lograr).
- Inversión en herramientas y capacitación.
- Refactoring de procesos heredados (legacy).

---

## 3. Trabajo práctico — Entrega de aplicación

Se debe entregar una aplicación cumpliendo:

- Desplegada en **Kubernetes**.
- Pipeline **CI/CD**.
- **Linting**, **TDD** y ejecución automática de pruebas.
- **Observabilidad** y **seguridad**.
- Presentación final del producto.

### Proyecto grupal (grupos de 2 o 3)

- Pensar un problema/proyecto a resolver durante el curso.
- Desarrollar una aplicación **contenerizada** y desplegada en **Kubernetes**.
- Desarrollar una **segunda versión** con un cambio mínimo, y alternar entre despliegues usando la estrategia **Blue/Green**.

#### ¿Qué es Blue/Green?

Estrategia de despliegue que consiste en tener dos entornos de producción en paralelo:

1. Se tiene un entorno activo (por ejemplo, el "azul") al cual los usuarios se siguen conectando con normalidad.
2. Se despliega la nueva versión en un segundo entorno ("verde").
3. Se prueba exhaustivamente esa nueva versión en el entorno verde, sin exponerla a usuarios reales.
4. Una vez validado que todo funciona correctamente, se redirige el tráfico de los clientes hacia el nuevo entorno (verde).

Esto permite hacer rollback rápido (volver al entorno anterior) si algo falla, ya que el entorno viejo queda intacto.

### Condiciones del entregable

- Stack tecnológico simple, nada sofisticado (uno o dos endpoints alcanza).
- **Dockerfile obligatorio**.
- Despliegue en **Minikube** o un clúster a elección.

---

## 4. Docker

### Historia pre-contenedores

**Antes de los contenedores:** Si una empresa quería publicar su aplicación tenía que:

- Comprar un servidor.
- Instalar las aplicaciones y dependencias que necesitaba la app.
- Configurar variables de ambiente, entre otras cosas.
- Hacer el deploy.

**Problemas que esto traía:**

- Seguir y actualizar cada dependencia y configuración manualmente.
- Mantener la infraestructura o arreglarla si se rompía.
- El equipo de infraestructura tenía que estimar las especificaciones del servidor de antemano.
- El servidor no estaba al 100% de carga la mayoría del tiempo (recursos desperdiciados).
- No se podía escalar ni correr muchas aplicaciones en el mismo servidor, ya que cada una requería su propio ambiente.

**Con las máquinas virtuales (VM):**

- Se pudo correr múltiples ambientes aislados en el mismo servidor físico.
- Se podían crear imágenes a partir de máquinas virtuales y reutilizarlas en diferentes servidores.

**Desafíos de las VM:**

- Eran pesadas: cada una requería su propio sistema operativo completo, lo que implica más uso de memoria, CPU y almacenamiento.
- Por naturaleza son más lentas, lo cual deteriora el rendimiento.

### ¿Qué es un contenedor?

Es un paquete **portable y liviano** de una aplicación, que incluye:

- El código.
- Las dependencias.
- Los archivos de configuración.
- Las variables de entorno.

**¿Por qué es posible esto?** Porque los contenedores comparten el **kernel del sistema operativo** en el que corren. Esto elimina la necesidad de correr un sistema operativo completo por cada copia de la aplicación (a diferencia de las VM).

### OCI — Open Container Initiative

Estándar para definir cómo se crean, distribuyen y ejecutan los contenedores. Los 3 componentes/especificaciones principales son:

- **Image spec** (especificación de imagen)
- **Runtime spec** (especificación de runtime)
- **Distribution spec** (especificación de distribución)

### CNCF — Cloud Native Computing Foundation

Fundación creada con el objetivo de promover y sostener tecnologías "cloud native" (nativas de la nube), como Kubernetes y otras herramientas del ecosistema de contenedores.

- Aquí es donde surge **Kubernetes**, creado para resolver el problema de la **orquestación de contenedores** (gestionar, escalar y coordinar múltiples contenedores en producción).

### Tecnologías de contenedores

- rkt
- Podman
- containerd
- **Docker**

### ¿Qué es Docker?

Es una plataforma para **desarrollar, empaquetar y desplegar** aplicaciones mediante contenedores.

Componentes que se van a mencionar en el curso:

- **Docker CLI**
- **Docker Engine**
- **Docker Runtime**
- **Docker Registries**

> [!info] Diferencias clave
> 
> - **Docker CLI**: es la herramienta de línea de comandos con la que se puede crear, correr, detener e interactuar con imágenes, contenedores y volúmenes de Docker.
> - **Docker Engine**: es la tecnología de contenerización de aplicaciones en sí; corre un proceso **daemon** en segundo plano que actúa como supervisor y permite todo el funcionamiento de los contenedores.
> - **Docker Runtime / Registries**: son las imágenes o los repositorios de imágenes existentes (hay muchos disponibles).
> - **Docker Registry**: es la ubicación centralizada (repositorio) para subir y descargar las aplicaciones que hagamos. Ejemplo: **Docker Hub**.

### Dockerfile

Es un documento de texto que define **cómo se va a crear la imagen** de un contenedor. Es básicamente una lista de pasos que se ejecutan para levantar la aplicación deseada.

En el Dockerfile se define, entre otras cosas:

- Librerías y sus versiones.
- Directorio de trabajo (dónde y en qué directorio se ejecuta).
- Si se quiere guardar logs.
- Comandos a ejecutar.
- Puertos que se van a exponer.

## Ejemplo de Dockerfile

```
# Imagen base sobre la que se construye
FROM node:20

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos los archivos de dependencias primero (aprovecha cache de Docker)
COPY package*.json ./

# Instalamos las dependencias
RUN npm install

# Copiamos el resto del código de la app
COPY . .

# Puerto que la app expone
EXPOSE 3000

# Variable de entorno de ejemplo
ENV NODE_ENV=production

# Comando que se ejecuta al levantar el contenedor
CMD ["node", "index.js"]


```