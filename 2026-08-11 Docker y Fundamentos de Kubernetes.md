# Clase 2026-08-11

## 1. Repaso: cómo funciona Docker

Docker construye **imágenes** a partir de un `Dockerfile`. Una imagen es una plantilla de solo lectura (código + dependencias + configuración). Cuando esa imagen se ejecuta, Docker crea un **contenedor**, que es la imagen "con vida": un proceso aislado corriendo a partir de esa plantilla.

- Docker **solo** crea imágenes a partir de Dockerfiles.
- Con esa imagen, Docker crea el contenedor (la ejecución).
- Un mismo Dockerfile/imagen puede generar múltiples contenedores independientes.

---

## 2. App de ejemplo: `notes-api`

Se diseñó una API en Python (FastAPI) para guardar notas, con 3 endpoints:

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Mensaje indicando que la API está activa |
| `POST` | `/add/{note}` | Agrega una nota con un texto (path param) |
| `GET` | `/list` | Lista todas las notas creadas |

### 2.1 Código

`notes-api/main.py` usa FastAPI y persiste las notas en un archivo JSON dentro de `data/notes.json`, para que sobrevivan a un reinicio del contenedor:

```python
import json
from pathlib import Path

from fastapi import FastAPI

app = FastAPI()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "notes.json"


def load_notes() -> list[str]:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_notes(notes: list[str]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


notes: list[str] = load_notes()


@app.get("/")
def root():
    return {"message": "API activa"}


@app.post("/add/{note}")
def add_note(note: str):
    notes.append(note)
    save_notes(notes)
    return {"message": "Nota agregada", "note": note}


@app.get("/list")
def list_notes():
    return {"notes": notes}
```

`notes-api/Dockerfile`:

```dockerfile
# Imagen base sobre la que se construye
FROM python:3.12-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero solo los requirements para aprovechar el cache de capas
COPY requirements.txt .

# Instalamos dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código de la app
COPY . .

# volumen de datos
VOLUME ["/app/data"]

# Comando que se ejecuta al levantar el contenedor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

El `VOLUME ["/app/data"]` marca ese directorio como punto de montaje persistente: aunque el contenedor se destruya, el contenido de `/app/data` (el `notes.json`) puede sobrevivir si se usa un volumen nombrado.

### 2.2 Construir la imagen

```bash
cd notes-api
docker build -t notes-api .
```

### 2.3 Levantar el contenedor (`docker run`)

Usando un volumen **nombrado** (`notes-data`) para persistir las notas fuera del ciclo de vida del contenedor, y publicando el puerto 8000:

```bash
docker run -d \
  --name notes-api-container \
  -p 8000:8000 \
  -v notes-data:/app/data \
  notes-api
```

- `-d`: modo *detached* (en segundo plano).
- `--name`: nombre del contenedor, para poder referenciarlo luego.
- `-p 8000:8000`: publica el puerto 8000 del contenedor en el puerto 8000 del host (`host:contenedor`).
- `-v notes-data:/app/data`: monta el volumen `notes-data` en `/app/data`, que es donde vive `notes.json`.

### 2.4 Revisar el volumen

Listar volúmenes y confirmar que existe:

```bash
docker volume ls --filter name=notes-data
```

Inspeccionarlo (muestra dónde vive físicamente en el host):

```bash
docker volume inspect notes-data
```

Salida real obtenida:

```json
[
    {
        "CreatedAt": "2026-08-11T22:22:25Z",
        "Driver": "local",
        "Labels": null,
        "Mountpoint": "/var/lib/docker/volumes/notes-data/_data",
        "Name": "notes-data",
        "Options": null,
        "Scope": "local"
    }
]
```

También se puede confirmar el montaje directamente sobre el contenedor:

```bash
docker inspect notes-api-container --format '{{json .Mounts}}'
```

### 2.5 Revisar los logs

```bash
docker logs notes-api-container
```

Para seguir los logs en vivo (como `tail -f`):

```bash
docker logs -f notes-api-container
```

Salida real (tras hacer las pruebas de la sección siguiente):

```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     192.168.65.1:33152 - "GET / HTTP/1.1" 200 OK
INFO:     192.168.65.1:48817 - "POST /add/comprar-cafe HTTP/1.1" 200 OK
INFO:     192.168.65.1:63491 - "GET /list HTTP/1.1" 200 OK
```

### 2.6 Probar los endpoints

**GET `/`** — verifica que la API está activa:

```bash
curl -s http://localhost:8000/
```

Respuesta real:

```json
{"message":"API activa"}
```

**POST `/add/{note}`** — agrega una nota (el texto va en la URL como path param):

```bash
curl -s -X POST http://localhost:8000/add/comprar-cafe
```

Respuesta real:

```json
{"message":"Nota agregada","note":"comprar-cafe"}
```

**GET `/list`** — lista todas las notas:

```bash
curl -s http://localhost:8000/list
```

Respuesta real:

```json
{"notes":["comprar-cafe"]}
```

> Nota: como el endpoint de agregar es `POST /add/{note}` con el texto embebido en la ruta, si la nota tiene espacios hay que codificarla en la URL, por ejemplo `curl -X POST http://localhost:8000/add/comprar%20cafe`.

### 2.7 Otros comandos útiles

```bash
# Ver contenedores corriendo
docker ps

# Entrar a una shell dentro del contenedor
docker exec -it notes-api-container bash

# Detener y eliminar el contenedor
docker stop notes-api-container
docker rm notes-api-container

# Eliminar también el volumen (borra las notas guardadas)
docker volume rm notes-data
```

---

## 3. Kubernetes

### 3.1 ¿Qué es Kubernetes y para qué sirve?

Kubernetes (K8s) es un **orquestador de contenedores**: automatiza el despliegue, escalado, recuperación ante fallos y gestión del ciclo de vida de aplicaciones contenerizadas. Docker crea y corre contenedores individuales; Kubernetes coordina **muchos** contenedores, en **muchos** servidores, como si fueran un solo sistema.

Cuando hablamos de Kubernetes, hablamos de un **clúster de Kubernetes**.

### 3.2 ¿Qué es un clúster?

Un clúster es un conjunto de servidores (físicos o virtuales) que juntan sus recursos (CPU, memoria, almacenamiento) y se comportan, de cara al usuario, como un único sistema.

Dentro del clúster hay dos tipos de servidores:

- **Plano de control (control plane / "la cabeza")**: toma las decisiones sobre el clúster (dónde correr qué, qué está sano, qué hay que reparar).
- **Nodos / workers**: servidores donde efectivamente corren las aplicaciones contenerizadas (dentro de Pods).

El plano de control elige en qué nodo levantar cada aplicación en base a configuración (afinidades, restricciones) y recursos disponibles (por ejemplo, cuánta CPU/memoria libre tiene cada nodo).

**Problema que resuelve Kubernetes:** sin él, si un contenedor se cae hay que levantarlo a mano; si un nodo entero se cae, hay que migrar sus cargas a mano. Kubernetes automatiza esto: si detecta que un contenedor o un nodo falló, reprograma automáticamente esos contenedores en un nodo sano, sin intervención humana.

### 3.3 Componentes de un clúster

Nos comunicamos con el clúster a través del **plano de control**, y los nodos existen como un detalle abstraído (no interactuamos con ellos directamente).

**En el plano de control:**

- **kube-apiserver (API de Kubernetes)**: es la puerta de entrada. Expone la API REST que interpreta y valida los comandos que enviamos (por ejemplo, vía `kubectl`). Todo componente del clúster, y todo usuario, habla con el clúster a través de esta API.
- **scheduler**: decide, en base a la configuración declarada y a los recursos disponibles, en qué nodo(s) se debe levantar cada Pod nuevo.
- **etcd**: base de datos clave-valor donde se guarda **todo** el estado del clúster (qué existe, su configuración, su estado deseado). Es la "fuente de la verdad" del clúster.
- **controller manager**: corre los "controladores", procesos que observan continuamente el estado actual vs. el estado deseado. Por ejemplo, si un Pod muere y el estado deseado dice que debe haber 3 réplicas corriendo, el controller manager es quien detecta la diferencia y dispara la creación de un Pod de reemplazo.

**En cada nodo:**

- **kubelet**: agente que corre en cada nodo y es quien interpreta las órdenes del plano de control (por ejemplo "levantá este Pod") y se asegura de que los contenedores de ese nodo estén efectivamente corriendo y saludables.
- **kube-proxy**: es quien maneja el networking del nodo: configura las reglas para que el tráfico llegue a los Pods correctos, incluyendo el enrutamiento hacia los Services.

### 3.4 Pod

Un **Pod** es la unidad más pequeña de despliegue en Kubernetes. No se despliegan contenedores sueltos: siempre se despliegan dentro de un Pod.

- Un Pod puede contener **uno o más contenedores** que comparten red y almacenamiento (el caso más común es un solo contenedor por Pod; múltiples contenedores se usan para patrones como *sidecar*).
- Ejemplo: un Pod que corre una API en Python.
- A cada Pod se le pueden (y conviene) definir **límites de CPU y memoria** (`limits`) — el tope máximo que puede consumir. Si un contenedor supera el límite de memoria, Kubernetes lo mata (OOMKill) y lo reinicia según la política de reinicio.

### 3.5 ReplicaSet

Un **ReplicaSet** es el objeto que asegura que siempre haya un número deseado de réplicas de un Pod ejecutándose. Si una réplica muere, el ReplicaSet crea otra para volver al número deseado.

En la práctica **casi nunca se crea un ReplicaSet directamente**: se gestiona indirectamente a través de un **Deployment**, que crea y administra el ReplicaSet por nosotros.

### 3.6 Deployment

Un **Deployment** es la forma declarativa recomendada de gestionar Pods y ReplicaSets. En vez de decirle a Kubernetes paso a paso qué hacer, declaramos el **estado deseado** (qué imagen, cuántas réplicas, qué recursos) y Kubernetes se encarga de alcanzarlo y mantenerlo.

Se usa para:

- **Escalar** la aplicación (subir o bajar el número de réplicas).
- Hacer **rollout** de nuevas versiones (actualizar la imagen de la app de forma controlada).
- Hacer **rollback** a una versión anterior si algo sale mal.

El manifiesto del Deployment incluye toda la información del Pod (imagen, puertos, recursos, variables de entorno, etc.) más el número de réplicas deseadas — Kubernetes usa esa plantilla para levantar tantos Pods como se pida.

### 3.7 Service

Los Pods son **efímeros**: se destruyen y recrean todo el tiempo (por un despliegue, un fallo, un reinicio), y cada vez que eso pasa cambian de IP interna. Un **Service** resuelve esto dando un punto de acceso **estable** (IP/DNS fijo) hacia un conjunto de Pods, sin importar cuáles Pods concretos estén vivos en cada momento (el Service los selecciona por *labels*).

Tipos principales:

- **ClusterIP** (por defecto): expone el Service solo dentro del clúster, con una IP interna estable.
- **NodePort**: además de lo anterior, abre un puerto fijo en **todos** los nodos del clúster para permitir acceso desde fuera.
- **LoadBalancer**: pide a la infraestructura subyacente (por ejemplo, un proveedor cloud) un balanceador de carga externo que enruta hacia el Service.

En resumen: si un Pod se cae y se recrea en otro nodo con otra IP, el Service sigue apuntando al mismo lugar desde afuera — nunca hablamos directamente con la IP de un Pod en producción.

### 3.8 Namespace

Un **Namespace** es una forma de organizar y aislar lógicamente los objetos dentro de un mismo clúster: permite agrupar las distintas aplicaciones o equipos (por ejemplo, `dev`, `staging`, `prod`, o un namespace por equipo), evitando colisiones de nombres y facilitando aplicar políticas o cuotas por grupo.

### 3.9 ConfigMap

Un **ConfigMap** guarda configuración no sensible que la aplicación necesita en tiempo de ejecución: variables de entorno, flags, archivos de configuración. Permite separar la configuración de la imagen de la aplicación, para no tener que reconstruir la imagen cada vez que cambia un valor de configuración.

### 3.10 Secret

Un **Secret** es conceptualmente igual a un ConfigMap (pares clave-valor que se inyectan en los Pods), pero pensado para **información sensible**: contraseñas, tokens, claves de API, certificados. Por defecto los valores se guardan codificados en base64 (no cifrados) dentro de `etcd`, por lo que en producción conviene combinarlos con cifrado en reposo o un gestor de secretos externo.

### 3.11 Volume

Como el almacenamiento de un contenedor se pierde cuando el contenedor muere, un **Volume** le da a los Pods acceso a almacenamiento que puede persistir más allá del ciclo de vida del Pod (o del contenedor dentro de él).

Existen (entre otros) dos conceptos principales:

- **Volume**: almacenamiento asociado directamente a la definición del Pod. Su ciclo de vida puede estar atado al del Pod según el tipo usado (aunque algunos tipos de volumen sí persisten más allá del Pod).
- **PersistentVolume (PV)** + **PersistentVolumeClaim (PVC)**: el PV es un recurso de almacenamiento provisto a nivel de clúster (independiente de cualquier Pod), y el PVC es la "solicitud" que hace un Pod para reservar y usar ese almacenamiento. Este mecanismo desacopla el almacenamiento del ciclo de vida del Pod: el PV puede sobrevivir aunque el Pod que lo usaba se elimine.

### 3.12 `requests` y `limits`

Antes de escribir un Deployment conviene tener claro esto:

- **`requests`**: la cantidad de CPU/memoria que el Pod tiene **garantizada**. El `scheduler` usa este valor para decidir en qué nodo cabe el Pod (solo lo coloca en un nodo que tenga al menos ese recurso disponible).
- **`limits`**: el **tope máximo** que el Pod puede llegar a consumir. Si un contenedor intenta usar más CPU de la que tiene de `limit`, se lo *throttlea* (se lo frena, no se lo mata); si intenta usar más memoria de la que tiene de `limit`, el contenedor es terminado (OOMKilled) y reiniciado.

En otras palabras: `requests` afecta **dónde** se agenda el Pod; `limits` afecta **qué tanto** puede crecer una vez corriendo. Definir ambos evita que una aplicación con una fuga de memoria o un pico de CPU afecte a los demás Pods del mismo nodo.

### 3.13 `kubectl`

`kubectl` es la **herramienta de línea de comandos** para interactuar con un clúster de Kubernetes. No habla directamente con los nodos: envía peticiones HTTP al `kube-apiserver` del plano de control, que es quien las valida, las persiste en `etcd` y coordina al resto de los componentes para cumplirlas.

Comandos típicos:

```bash
kubectl get pods                 # listar pods
kubectl get deployments          # listar deployments
kubectl describe pod <nombre>    # detalle y eventos de un pod
kubectl apply -f deployment.yaml # aplicar/crear un recurso desde un manifiesto
kubectl logs <pod>               # ver logs de un pod
kubectl delete -f deployment.yaml
```

### 3.14 `minikube`

`minikube` es una herramienta que levanta un **clúster de Kubernetes local de un solo nodo** (normalmente dentro de una VM o contenedor) en la máquina de desarrollo. Sirve para aprender, probar y desarrollar manifiestos de Kubernetes sin necesitar un clúster real en la nube, ya que replica el comportamiento de un clúster completo (control plane + nodo) a escala reducida.

Uso típico:

```bash
minikube start        # levanta el clúster local
kubectl get nodes      # minikube ya deja kubectl apuntando a este clúster
minikube dashboard     # UI web para explorar el clúster
minikube stop          # apaga el clúster
```

---

## 4. Anatomía de un YAML de Deployment (nginx)

```yaml
# apiVersion: versión de la API de Kubernetes que define el esquema de este objeto.
# "apps/v1" es la API estable para Deployments.
apiVersion: apps/v1

# kind: tipo de objeto que estamos declarando.
kind: Deployment

# metadata: información identificatoria del objeto en sí (el Deployment),
# no de los pods que va a crear.
metadata:
  name: nginx-deployment        # nombre único del Deployment dentro del namespace
  namespace: default            # namespace donde vive este objeto
  labels:
    app: nginx                  # etiquetas propias del Deployment (organización/selección)

# spec: el "estado deseado" del Deployment. Todo lo que Kubernetes debe
# mantener cierto a lo largo del tiempo.
spec:
  replicas: 3                   # cantidad deseada de Pods corriendo en paralelo

  # selector: le dice al Deployment qué Pods son "suyos" para gestionar
  # (debe coincidir exactamente con las labels de template.metadata.labels).
  selector:
    matchLabels:
      app: nginx

  # strategy: cómo se reemplazan los Pods viejos por nuevos al actualizar
  # la imagen (rollout).
  strategy:
    type: RollingUpdate         # reemplaza pods de a poco, sin downtime total
    rollingUpdate:
      maxUnavailable: 1         # cuántos pods pueden estar caídos durante el update
      maxSurge: 1               # cuántos pods extra puede crear temporalmente

  # template: la "plantilla" de Pod que el Deployment usa para crear cada réplica.
  # Todo lo de acá abajo es, en esencia, la definición de un Pod.
  template:
    metadata:
      labels:
        app: nginx               # debe matchear con spec.selector.matchLabels

    spec:
      containers:
        - name: nginx             # nombre del contenedor dentro del pod
          image: nginx:1.27       # imagen y tag específico (evitar "latest" en prod)

          ports:
            - containerPort: 80    # puerto en el que escucha el proceso dentro del contenedor

          # requests: recursos garantizados; el scheduler solo coloca este pod
          # en un nodo que tenga al menos esto disponible.
          # limits: tope máximo que puede llegar a consumir el contenedor.
          resources:
            requests:
              cpu: "100m"          # 100 millicores = 0.1 vCPU
              memory: "128Mi"
            limits:
              cpu: "250m"
              memory: "256Mi"

          # variables de entorno inyectadas desde un ConfigMap
          envFrom:
            - configMapRef:
                name: nginx-config

          # volumen montado dentro del contenedor (ver volumes más abajo)
          volumeMounts:
            - name: nginx-html
              mountPath: /usr/share/nginx/html

          # livenessProbe: si falla repetidamente, Kubernetes reinicia el contenedor
          # (detecta que el proceso está "colgado" aunque siga vivo).
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 10

          # readinessProbe: si falla, el pod se saca temporalmente del Service
          # (no recibe tráfico) hasta que vuelva a responder OK.
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 5

      # volumes: define el almacenamiento a nivel de Pod que luego se
      # referencia en volumeMounts de cada contenedor.
      volumes:
        - name: nginx-html
          persistentVolumeClaim:
            claimName: nginx-html-pvc   # reserva de almacenamiento vía un PVC
```

**Resumen de la jerarquía:**

- `apiVersion` + `kind` → qué tipo de objeto es.
- `metadata` → identidad del propio Deployment (nombre, namespace, labels).
- `spec.replicas` / `spec.selector` / `spec.strategy` → cómo se comporta el Deployment como controlador.
- `spec.template` → la definición completa de **un Pod**, que el Deployment clona `replicas` veces.
- Dentro del Pod: `containers` (imagen, puertos, `resources`, `env`/`envFrom`, `volumeMounts`, *probes*) y `volumes` (de dónde sale el almacenamiento que se monta).

Este Deployment por sí solo **no expone nginx de forma estable hacia afuera** — para eso hace falta además un `Service` (ver sección 3.7) que seleccione los Pods vía `app: nginx`.

---

## 5. Actividad: Deployment de 3 instancias de `notes-api`, cada una con su propia configuración

Enunciado de la actividad:

> Escribir un manifest de k8s que declare un Deployment con 3 instancias de la aplicación de notas. Cada instancia debe tener un parámetro distinto en el título del API, la web inicial, o el parámetro de health. Este debe ser especificado mediante un ConfigMap. Instalar minikube e iniciar el deployment con `kubectl`.

No te preocupes si algo no te cierra a la primera lectura: la idea de esta sección es que entiendas el *por qué* de cada decisión, no solo copiar comandos.

### 5.1 Antes de arrancar: una trampita del enunciado

El enunciado pide "un Deployment con 3 instancias" pero también que "cada instancia tenga un parámetro distinto". Estas dos frases, leídas juntas, esconden un malentendido muy común cuando uno recién está aprendiendo Kubernetes.

Repasá la sección 3.6: un Deployment tiene **un solo** `spec.template` (la "receta" del Pod), y `spec.replicas` le dice a Kubernetes cuántas copias **idénticas** de esa receta tiene que mantener corriendo. Es decir, si vos hacés **un** Deployment con `replicas: 3`, Kubernetes te va a crear 3 Pods clonados a partir del mismo template — con el mismo ConfigMap, las mismas variables de entorno, todo igual. No hay forma de que el Pod 1 reciba un valor de ConfigMap distinto al Pod 2 si ambos salen del mismo Deployment, porque el Deployment no sabe "diferenciar" sus propias réplicas entre sí.

Entonces, ¿cómo logramos que cada instancia tenga una configuración distinta? La solución es crear **3 Deployments separados**, cada uno con `replicas: 1`, y cada uno apuntando a **su propio ConfigMap**. Cada Deployment es una "instancia" de la aplicación con su propia identidad y su propia configuración; entre los tres suman las 3 instancias que pide el enunciado. Es un poco más de YAML para escribir, pero es la única forma correcta de lograr esto con las piezas que ya conocemos (Deployment + ConfigMap).

### 5.2 Preparar la app para que lea su configuración desde variables de entorno

Un ConfigMap no le "inyecta magia" a tu código: lo que hace, en la práctica, es dejar disponibles variables de entorno (o archivos) dentro del contenedor. Si tu aplicación tiene los valores *hardcodeados* en el código (como estaba `notes-api` hasta ahora, con `"API activa"` fijo en el `return`), el ConfigMap no tiene nada para cambiar. El primer paso, entonces, **no es de Kubernetes, es de la aplicación**: hay que hacer que `main.py` lea esos valores desde el entorno, con un default razonable por si la variable no está seteada (por ejemplo, corriendo la app local con `uvicorn` sin Kubernetes de por medio).

Se modificó `notes-api/main.py` así:

```python
import json
import os
from pathlib import Path

from fastapi import FastAPI

API_TITLE = os.getenv("API_TITLE", "notes-api")
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "API activa")
HEALTH_STATUS = os.getenv("HEALTH_STATUS", "ok")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "default")

app = FastAPI(title=API_TITLE)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "notes.json"


def load_notes() -> list[str]:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_notes(notes: list[str]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


notes: list[str] = load_notes()


@app.get("/")
def root():
    return {"message": WELCOME_MESSAGE, "title": API_TITLE, "instance": INSTANCE_NAME}


@app.post("/add/{note}")
def add_note(note: str):
    notes.append(note)
    save_notes(notes)
    return {"message": "Nota agregada", "note": note}


@app.get("/list")
def list_notes():
    return {"notes": notes}


@app.get("/health")
def health():
    return {"status": HEALTH_STATUS, "instance": INSTANCE_NAME}
```

Cuatro cosas para notar acá, porque cada una responde a una parte del enunciado:

- `API_TITLE` cambia el **título del API** (se lo pasamos a `FastAPI(title=...)`, que es lo que se muestra en la documentación automática en `/docs`).
- `WELCOME_MESSAGE` cambia la **web inicial** (la respuesta de `GET /`).
- `HEALTH_STATUS` es el **parámetro de health**. Como la app original no tenía ningún endpoint de salud, se agregó `GET /health`, que es el patrón estándar que usan los orquestadores (incluido Kubernetes, con sus `livenessProbe`/`readinessProbe` de la sección 4) para preguntarle a una app "¿estás bien?".
- `INSTANCE_NAME` no lo pide el enunciado explícitamente, pero se agregó para poder confirmar a simple vista, al hacer `curl`, con qué instancia estamos hablando. Es una ayuda para nosotros como desarrolladores/estudiantes, no un requisito de Kubernetes.

Todas usan `os.getenv("X", "default")`: si la variable de entorno no existe, la app igual arranca con un valor por defecto. Esto es una buena práctica — la app no debería romperse si alguien la corre sin Kubernetes.

### 5.3 Reconstruir la imagen Docker

Como cambiamos el código de la app, la imagen Docker que ya teníamos construida (sección 2.2) quedó vieja: todavía tiene el `main.py` sin las variables de entorno. Kubernetes no "ve" tu código fuente, solo ve imágenes de contenedor — así que si no reconstruimos la imagen, vamos a estar desplegando la versión anterior sin darnos cuenta.

```bash
cd notes-api
docker build -t notes-api:k8s .
```

Le pusimos el tag `k8s` (en vez de reusar `latest` o el nombre de antes) simplemente para diferenciarla con claridad de la imagen que usamos en la sección 2 con `docker run` directo — es una convención prolija, no una obligación.

Salida real obtenida (algunas capas se reutilizan del build anterior gracias al cache de Docker, por eso dice `CACHED`):

```
#6 [3/5] COPY requirements.txt .
#6 CACHED

#7 [2/5] WORKDIR /app
#7 CACHED

#8 [4/5] RUN pip install --no-cache-dir -r requirements.txt
#8 CACHED

#9 [5/5] COPY . .
#9 DONE 0.4s

#10 exporting to image
#10 exporting layers 0.1s done
#10 writing image sha256:666941b2b37a0428fed755f379a6725d177243dd80cb0f180a225e35a8a61bac done
#10 naming to docker.io/library/notes-api:k8s done
```

### 5.4 Instalar minikube

Recordá la sección 3.14: `minikube` levanta un clúster de Kubernetes real (control plane + nodo), pero corriendo localmente en tu máquina, pensado para aprender y desarrollar sin depender de un clúster en la nube. En macOS, la forma más simple de instalarlo es con Homebrew:

```bash
brew install minikube
```

Esto también instaló `kubernetes-cli` (el paquete que provee `kubectl`) como dependencia, en caso de que no lo tuvieras. Salida real (resumida):

```
==> Installing minikube dependency: kubernetes-cli
==> Pouring kubernetes-cli--1.36.3.arm64_tahoe.bottle.tar.gz
🍺  /opt/homebrew/Cellar/kubernetes-cli/1.36.3: 261 files, 62.5MB
==> Installing minikube
==> Pouring minikube--1.38.1.arm64_tahoe.bottle.tar.gz
🍺  /opt/homebrew/Cellar/minikube/1.38.1: 11 files, 135.7MB
```

### 5.5 Levantar el clúster con el driver de Docker

`minikube` necesita algo sobre lo cual correr su "nodo" (que en realidad es un contenedor o una VM que simula ser un nodo completo de Kubernetes). Como ya teníamos Docker Desktop corriendo, usamos el **driver de Docker**: minikube crea un contenedor especial (`kicbase`) que por dentro corre todos los componentes del clúster (`kube-apiserver`, `etcd`, `kubelet`, etc., de la sección 3.3).

```bash
minikube start --driver=docker
```

La primera vez que se corre, este comando tarda varios minutos porque tiene que descargar la imagen base del nodo (~480 MB) y la de Kubernetes. Para confirmar que terminó bien y que todo quedó arriba:

```bash
minikube status
```

Salida real obtenida:

```
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured
```

El último renglón, `kubeconfig: Configured`, es importante: significa que `minikube` ya modificó la configuración de `kubectl` en tu máquina para que apunte a este clúster local automáticamente. Por eso, a partir de acá, cualquier `kubectl get ...` que corramos va a hablar con el clúster de minikube sin que tengamos que indicarle nada extra.

### 5.6 Pasar nuestra imagen al clúster de minikube

Este es un paso en el que mucha gente se traba la primera vez, así que vale la pena explicarlo bien. Cuando usás el driver de Docker, minikube corre **su propio Docker por dentro**, aislado del Docker de tu máquina (el host). Es decir: que vos hayas hecho `docker build -t notes-api:k8s .` en tu terminal **no significa que esa imagen exista dentro del clúster**. Son dos "Dockers" distintos que no comparten imágenes automáticamente.

Si en este punto escribiéramos el Deployment apuntando a `notes-api:k8s` tal cual, Kubernetes intentaría bajar esa imagen de Docker Hub (el registro público por defecto) y fallaría, porque `notes-api` no es una imagen pública que exista ahí — es una que armamos nosotros localmente.

Hay varias formas de resolver esto (construir la imagen directamente "dentro" del entorno Docker de minikube, subirla a un registro, etc.); la más directa para uso local es pedirle a minikube que copie la imagen que ya construimos:

```bash
minikube image load notes-api:k8s
```

Este comando no imprime nada si sale bien. Para confirmar que la imagen quedó disponible adentro del clúster:

```bash
minikube image ls | grep notes-api
```

Salida real obtenida:

```
docker.io/library/notes-api:k8s
```

### 5.7 Escribir los manifiestos: un ConfigMap + un Deployment por instancia

Ahora sí, la parte central de la actividad. Siguiendo lo que explicamos en 5.1, se creó una carpeta `notes-api/k8s/` con **tres archivos**, uno por instancia. Cada archivo contiene dos objetos separados por `---` (así es como YAML permite declarar varios documentos en un mismo archivo): un `ConfigMap` y el `Deployment` que lo consume.

Este es el contenido completo de `k8s/instancia-1.yaml` (los otros dos son análogos, solo cambia el número):

```yaml
# ConfigMap: guarda la configuración de ESTA instancia como pares clave-valor.
# No hace nada por sí solo: recién cobra efecto cuando un contenedor lo
# referencia (ver envFrom más abajo, en el Deployment).
apiVersion: v1
kind: ConfigMap
metadata:
  name: notes-api-config-1        # nombre con el que el Deployment lo va a referenciar
data:
  API_TITLE: "notes-api-instancia-1"                     # título del API (FastAPI(title=...))
  WELCOME_MESSAGE: "Bienvenido a la instancia 1 de notes-api"  # respuesta de GET /
  HEALTH_STATUS: "ok-instancia-1"                        # respuesta de GET /health
  INSTANCE_NAME: "instancia-1"                           # identificador para distinguir la instancia al hacer curl
---
# Deployment: la "instancia 1" en sí. Con replicas: 1 y su propio ConfigMap,
# queda desacoplado de las otras dos instancias (ver sección 5.1: un solo
# Deployment con replicas: 3 no permite configuración distinta por Pod).
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notes-api-deployment-1      # nombre único de este Deployment dentro del namespace
  labels:
    app: notes-api                  # label común a las 3 instancias (para verlas agrupadas)
    instance: instancia-1           # label que identifica a ESTA instancia puntual

spec:
  replicas: 1                       # una sola réplica: cada instancia es un Deployment aparte

  # selector: qué Pods pertenecen a este Deployment. Incluye "instance" además
  # de "app" para que no se solape con los selectores de las otras 2 instancias
  # (si solo usara "app: notes-api", Kubernetes rechazaría el manifiesto por
  # ambigüedad entre Deployments).
  selector:
    matchLabels:
      app: notes-api
      instance: instancia-1

  # template: la definición del Pod que este Deployment crea y mantiene.
  template:
    metadata:
      labels:
        app: notes-api
        instance: instancia-1       # debe coincidir con spec.selector.matchLabels

    spec:
      containers:
        - name: notes-api
          image: notes-api:k8s          # imagen construida localmente y cargada con `minikube image load`
          imagePullPolicy: IfNotPresent # no intentar bajarla de un registro remoto, usar la que ya está en el nodo

          ports:
            - containerPort: 8000       # puerto en el que escucha uvicorn dentro del contenedor

          # envFrom + configMapRef: vuelca TODAS las claves del ConfigMap
          # como variables de entorno del contenedor. main.py las lee con
          # os.getenv("API_TITLE", ...), etc.
          envFrom:
            - configMapRef:
                name: notes-api-config-1
```

Puntos clave para entender, uno por uno:

- **El `ConfigMap` no tiene "receta de Pod"**, es solo un diccionario de clave-valor (`data:`). No hace nada por sí solo — necesita que algo lo referencie.
- **`envFrom.configMapRef.name`** es la parte que conecta el ConfigMap con el contenedor: le dice a Kubernetes "tomá **todas** las claves de este ConfigMap y volcalas como variables de entorno dentro del contenedor". Como en `main.py` usamos exactamente esos mismos nombres (`API_TITLE`, `WELCOME_MESSAGE`, etc.) con `os.getenv(...)`, la app las va a recoger automáticamente al arrancar. (La alternativa más verbosa, `env` con `valueFrom.configMapKeyRef`, permite traer una clave puntual y hasta renombrarla; acá usamos `envFrom` porque queremos todas las claves tal cual están.)
- **`replicas: 1`**: cada Deployment es una sola instancia, como definimos en 5.1. Si quisiéramos que la "instancia 1" tuviera alta disponibilidad, podríamos subir esto a 2 o 3 — pero ojo, esas réplicas adicionales seguirían compartiendo la configuración de `notes-api-config-1`, siempre según lo explicado antes.
- **`selector.matchLabels` y `template.metadata.labels` incluyen `instance: instancia-1`**, no solo `app: notes-api`. Esto es fundamental: si los tres Deployments usaran como selector únicamente `app: notes-api`, los tres intentarían "adoptar" los mismos Pods (los de las otras instancias también matchean esa label), y Kubernetes tira un error de validación porque un Deployment no puede tener un selector que se superponga con el de otro. Agregar `instance: instancia-N` como parte de la label y del selector evita esa colisión y, de paso, nos deja identificar de un vistazo a qué instancia pertenece cada Pod con `kubectl get pods --show-labels`.
- **`imagePullPolicy: IfNotPresent`**: le dice a Kubernetes "si ya tenés esta imagen localmente (en este caso, porque la cargamos con `minikube image load`), usala tal cual; no intentes bajarla de ningún registro". Sin esto, el valor por defecto de Kubernetes para imágenes sin un tag `latest` también es `IfNotPresent`, pero dejarlo explícito documenta la intención y evita sorpresas.

### 5.8 Aplicar los manifiestos con `kubectl`

Con los tres archivos en `notes-api/k8s/`, se aplican todos juntos apuntando a la carpeta (`kubectl apply -f` acepta tanto un archivo como un directorio, y en ese caso aplica todos los `.yaml` que encuentre):

```bash
kubectl apply -f k8s/
```

Salida real obtenida:

```
configmap/notes-api-config-1 created
deployment.apps/notes-api-deployment-1 created
configmap/notes-api-config-2 created
deployment.apps/notes-api-deployment-2 created
configmap/notes-api-config-3 created
deployment.apps/notes-api-deployment-3 created
```

Notá que `kubectl` reporta la creación de **6 objetos**: 3 ConfigMaps + 3 Deployments — coherente con la decisión de 5.1 de usar un Deployment por instancia en vez de uno solo con `replicas: 3`.

Verificamos que todo haya quedado sano:

```bash
kubectl get pods -o wide
kubectl get deployments
kubectl get configmaps
```

Salida real obtenida:

```
NAME                                      READY   STATUS    RESTARTS   AGE
notes-api-deployment-1-5cf6f9cd9-fkdxl    1/1     Running   0          9s
notes-api-deployment-2-fd4588c4f-8jl88    1/1     Running   0          9s
notes-api-deployment-3-69657cdf7-fv55m    1/1     Running   0          9s

NAME                     READY   UP-TO-DATE   AVAILABLE   AGE
notes-api-deployment-1   1/1     1            1           9s
notes-api-deployment-2   1/1     1            1           9s
notes-api-deployment-3   1/1     1            1           9s

NAME                 DATA   AGE
kube-root-ca.crt     1      113s
notes-api-config-1   4      9s
notes-api-config-2   4      9s
notes-api-config-3   4      9s
```

Los tres Deployments están `1/1` (un Pod deseado, un Pod corriendo) y cada ConfigMap tiene `DATA: 4`, que son las 4 claves que definimos en cada uno.

### 5.9 Confirmar que cada instancia realmente tiene su propia configuración

Falta la prueba de fuego: verificar que el ConfigMap efectivamente cambió el comportamiento de cada Pod. Como estos Pods todavía no tienen un `Service` que los exponga (ver sección 3.7 — acá optamos por no agregar uno para no sumar complejidad a una actividad que ya tiene varias piezas nuevas), usamos `kubectl port-forward` para abrir un túnel temporal desde un puerto de nuestra máquina hacia el puerto 8000 de cada Deployment:

```bash
kubectl port-forward deployment/notes-api-deployment-1 8001:8000 &
kubectl port-forward deployment/notes-api-deployment-2 8002:8000 &
kubectl port-forward deployment/notes-api-deployment-3 8003:8000 &
```

`port-forward` es una herramienta de **desarrollo/depuración**, no la forma en la que se expone una app en producción (para eso está el `Service`) — pero es perfecta para este tipo de verificación rápida y local.

Con los tres túneles abiertos, probamos la raíz (`/`) y el health check (`/health`) de cada instancia:

```bash
curl -s http://localhost:8001/
curl -s http://localhost:8001/health
curl -s http://localhost:8002/
curl -s http://localhost:8002/health
curl -s http://localhost:8003/
curl -s http://localhost:8003/health
```

Salida real obtenida:

```json
{"message":"Bienvenido a la instancia 1 de notes-api","title":"notes-api-instancia-1","instance":"instancia-1"}
{"status":"ok-instancia-1","instance":"instancia-1"}
{"message":"Bienvenido a la instancia 2 de notes-api","title":"notes-api-instancia-2","instance":"instancia-2"}
{"status":"ok-instancia-2","instance":"instancia-2"}
{"message":"Bienvenido a la instancia 3 de notes-api","title":"notes-api-instancia-3","instance":"instancia-3"}
{"status":"ok-instancia-3","instance":"instancia-3"}
```

Cada instancia responde con su propio mensaje de bienvenida, su propio título y su propio estado de health — exactamente lo que pedía el enunciado, y todo controlado únicamente desde el `ConfigMap` de cada una, sin haber tocado la imagen Docker entre instancia e instancia (las tres usan **la misma imagen** `notes-api:k8s`; lo único que cambia es qué ConfigMap le inyecta cada Deployment).

Al terminar de probar, no te olvides de cerrar los túneles (si los corriste en primer plano, `Ctrl+C`; si los mandaste a segundo plano con `&` como acá, `kill %1 %2 %3` o `pkill -f "kubectl port-forward"`).

### 5.10 Comandos útiles para inspeccionar

```bash
# Ver a qué instancia pertenece cada pod
kubectl get pods --show-labels

# Ver el detalle de un Deployment puntual (eventos, imagen usada, réplicas)
kubectl describe deployment notes-api-deployment-1

# Ver el contenido de un ConfigMap
kubectl describe configmap notes-api-config-1
```

> Para bajar todo lo que levantamos en esta actividad (y volver a levantarlo después), ver la sección 6.

### 5.11 Resumen del recorrido

1. Nos dimos cuenta de que "3 instancias con configuración distinta" en realidad requiere **3 Deployments** (uno por instancia), no un único Deployment con `replicas: 3` — porque todas las réplicas de un mismo Deployment son clones idénticos.
2. Modificamos `notes-api/main.py` para que el título, el mensaje inicial y el estado de health salgan de variables de entorno en vez de estar *hardcodeados*.
3. Reconstruimos la imagen Docker (`docker build`) porque el código cambió.
4. Instalamos minikube y levantamos un clúster local de Kubernetes con `minikube start --driver=docker`.
5. Cargamos la imagen construida localmente adentro del clúster con `minikube image load`, porque el Docker del host y el Docker interno de minikube no comparten imágenes automáticamente.
6. Escribimos un `ConfigMap` + `Deployment` por instancia, usando `envFrom.configMapRef` para inyectar la configuración y labels distintas (`instance: instancia-N`) para que los selectores no colisionen entre Deployments.
7. Aplicamos todo con `kubectl apply -f k8s/` y confirmamos con `kubectl get` que los tres Pods estaban `Running`.
8. Verificamos con `kubectl port-forward` + `curl` que cada instancia efectivamente respondía con su propia configuración.

---

## 6. Finalmente, podemos bajar todos los servicios

Durante la clase quedaron **tres cosas distintas** corriendo en la máquina: el contenedor de Docker de la sección 2 (`notes-api-container`), el clúster de minikube, y adentro de ese clúster, los 3 Deployments/ConfigMaps de la actividad. Vamos a bajar todo, pero de una forma **reversible**: la idea es poder cerrar la notebook hoy y, mañana, levantar todo de nuevo sin tener que rehacer los pasos desde cero.

Para eso hay que tener clara una distinción que ya usamos varias veces en la nota (secciones 3.6 y 5.1) pero que vale la pena remarcar acá: **"bajar/detener" no es lo mismo que "borrar/eliminar"**.

- **Detener** (`docker stop`, `minikube stop`) apaga el proceso pero conserva su estado guardado en disco: el contenedor sigue existiendo (solo que apagado), el clúster de minikube sigue existiendo con todas sus imágenes cacheadas. Volver a levantarlo es rápido.
- **Eliminar** (`docker rm`, `kubectl delete`, `minikube delete`) borra el objeto en sí. Algunas cosas eliminadas se recrean fácilmente porque tenemos su "receta" guardada en un archivo (un manifiesto YAML, un `docker run`); otras, como los datos dentro de un volumen, si eliminás el volumen se pierden para siempre.

Vamos a bajar todo en el orden inverso al que lo levantamos: primero lo que corre **adentro** del clúster, después el clúster, y por último el contenedor suelto de Docker.

### 6.1 Bajar los recursos de Kubernetes (los 3 Deployments + los 3 ConfigMaps)

Como guardamos la configuración de la actividad en archivos YAML dentro de `notes-api/k8s/`, no hace falta acordarse de los nombres de cada Deployment o ConfigMap para borrarlos uno por uno: le podemos decir a `kubectl` que borre "todo lo que está descripto en esta carpeta", con el mismo flag `-f` que usamos para crearlos:

```bash
kubectl delete -f k8s/
```

Salida real obtenida:

```
configmap "notes-api-config-1" deleted from default namespace
deployment.apps "notes-api-deployment-1" deleted from default namespace
configmap "notes-api-config-2" deleted from default namespace
deployment.apps "notes-api-deployment-2" deleted from default namespace
configmap "notes-api-config-3" deleted from default namespace
deployment.apps "notes-api-deployment-3" deleted from default namespace
```

Confirmamos que no quedó ningún Pod corriendo:

```bash
kubectl get pods
```

Salida real obtenida:

```
No resources found in default namespace.
```

Importante: esto borra los **objetos de Kubernetes** (Deployments, ConfigMaps, y por lo tanto sus Pods), pero **no** toca ni el clúster de minikube ni la imagen `notes-api:k8s` que ya habíamos cargado adentro con `minikube image load` (sección 5.6). Esa imagen queda cacheada en el clúster. Es justamente por eso que, para volver a levantar la actividad, alcanza con un `kubectl apply -f k8s/` — no hace falta repetir el `docker build` ni el `minikube image load` (a menos que hayas cambiado el código de la app o eliminado el clúster entero, ver 6.2).

### 6.2 Apagar el clúster de minikube

Con los recursos de adentro ya bajados, apagamos el clúster en sí:

```bash
minikube stop
```

Salida real obtenida:

```
* Stopping node "minikube"  ...
* Powering off "minikube" via SSH ...
* 1 node stopped.
```

`minikube stop` apaga el contenedor `kicbase` que simula el nodo (sección 3.14 y 5.5), pero **no lo elimina**: todo el disco del "nodo" queda guardado tal cual estaba, incluida la imagen `notes-api:k8s` que cargamos. Lo confirmamos con:

```bash
minikube status
```

Salida real obtenida:

```
minikube
type: Control Plane
host: Stopped
kubelet: Stopped
apiserver: Stopped
kubeconfig: Stopped
```

> Si en algún momento querés liberar por completo el espacio en disco que usa minikube (por ejemplo, se te quedó sin espacio la máquina), la opción es `minikube delete` en lugar de `minikube stop`. Pero ojo: `delete` borra el nodo entero, incluida la imagen que cargamos — la próxima vez habría que repetir `minikube start` **y** `minikube image load notes-api:k8s` (sección 5.5 y 5.6) antes de poder hacer `kubectl apply` de nuevo. Para "pausar y seguir mañana", `minikube stop` es lo correcto.

### 6.3 Detener el contenedor Docker de la sección 2

Por último, el contenedor que levantamos "a mano" con `docker run` en la sección 2.3, por fuera de todo lo de Kubernetes:

```bash
docker stop notes-api-container
```

Salida real obtenida:

```
notes-api-container
```

(Docker imprime el nombre del contenedor que efectivamente detuvo, a modo de confirmación.) Verificamos su estado:

```bash
docker ps -a --filter name=notes-api-container
```

Salida real obtenida:

```
CONTAINER ID   IMAGE          COMMAND                  CREATED        STATUS                    PORTS     NAMES
3d10e317e21c   d21fdebbd061   "uvicorn main:app --…"   41 hours ago   Exited (0) ...             notes-api-container
```

Pasó de `Up ...` a `Exited (0) ...`: el contenedor sigue existiendo (por eso `docker ps -a`, con la `-a`, todavía lo lista), solo que apagado. El volumen nombrado `notes-data` (sección 2.3/2.4), que es donde vive `notes.json`, es un recurso **aparte** del contenedor: sigue intacto con todas las notas guardadas, se haya detenido o no el contenedor.

Usamos `docker stop` y no `docker rm` a propósito: `rm` directamente eliminaría el contenedor (no el volumen, que sobreviviría igual), y para volver a levantarlo habría que ejecutar de nuevo el `docker run` completo de la sección 2.3. Con `stop`, alcanza con un `docker start` para retomarlo tal cual estaba.

### 6.4 Cómo levantar todo de nuevo

Guardate esta receta para la próxima clase. En el mismo orden en el que bajamos las cosas, pero al revés:

```bash
# 1. Contenedor "suelto" de la sección 2 (si lo querés usar de nuevo)
docker start notes-api-container

# 2. Clúster de minikube
minikube start --driver=docker

# 3. Los 3 Deployments + ConfigMaps de la actividad
#    (no hace falta repetir docker build ni minikube image load,
#    porque el clúster conservó la imagen al hacer `minikube stop`
#    en vez de `minikube delete`)
cd notes-api
kubectl apply -f k8s/

# 4. Confirmar que volvió todo
kubectl get pods
```

Si en cambio en algún momento usaste `minikube delete`, tenés que reconstruir la imagen si cambiaste código (`docker build -t notes-api:k8s .`, sección 5.3) y volver a cargarla en el clúster nuevo (`minikube image load notes-api:k8s`, sección 5.6) antes del `kubectl apply -f k8s/`.
