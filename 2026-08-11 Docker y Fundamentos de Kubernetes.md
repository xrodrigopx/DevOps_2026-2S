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

> La actividad práctica de esta clase (Deployment de 3 instancias de `notes-api` con minikube) se separó a su propia nota: [[2026-08-11-2 Actividad Docker k8s minikube]].

## 5. Finalmente, podemos bajar todos los servicios

Durante la clase quedaron **tres cosas distintas** corriendo en la máquina: el contenedor de Docker de la sección 2 (`notes-api-container`), el clúster de minikube, y adentro de ese clúster, los 3 Deployments/ConfigMaps de la actividad. Vamos a bajar todo, pero de una forma **reversible**: la idea es poder cerrar la notebook hoy y, mañana, levantar todo de nuevo sin tener que rehacer los pasos desde cero.

Para eso hay que tener clara una distinción que ya usamos varias veces en la nota (sección 3.6 y sección [[2026-08-11-2 Actividad Docker k8s minikube#1. Antes de arrancar: una trampita del enunciado|1]] de la actividad) pero que vale la pena remarcar acá: **"bajar/detener" no es lo mismo que "borrar/eliminar"**.

- **Detener** (`docker stop`, `minikube stop`) apaga el proceso pero conserva su estado guardado en disco: el contenedor sigue existiendo (solo que apagado), el clúster de minikube sigue existiendo con todas sus imágenes cacheadas. Volver a levantarlo es rápido.
- **Eliminar** (`docker rm`, `kubectl delete`, `minikube delete`) borra el objeto en sí. Algunas cosas eliminadas se recrean fácilmente porque tenemos su "receta" guardada en un archivo (un manifiesto YAML, un `docker run`); otras, como los datos dentro de un volumen, si eliminás el volumen se pierden para siempre.

Vamos a bajar todo en el orden inverso al que lo levantamos: primero lo que corre **adentro** del clúster, después el clúster, y por último el contenedor suelto de Docker.

### 5.1 Bajar los recursos de Kubernetes (los 3 Deployments + los 3 ConfigMaps)

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

Importante: esto borra los **objetos de Kubernetes** (Deployments, ConfigMaps, y por lo tanto sus Pods), pero **no** toca ni el clúster de minikube ni la imagen `notes-api:k8s` que ya habíamos cargado adentro con `minikube image load` (sección [[2026-08-11-2 Actividad Docker k8s minikube#6. Pasar nuestra imagen al clúster de minikube|6 de la actividad]]). Esa imagen queda cacheada en el clúster. Es justamente por eso que, para volver a levantar la actividad, alcanza con un `kubectl apply -f k8s/` — no hace falta repetir el `docker build` ni el `minikube image load` (a menos que hayas cambiado el código de la app o eliminado el clúster entero, ver 5.2).

### 5.2 Apagar el clúster de minikube

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

`minikube stop` apaga el contenedor `kicbase` que simula el nodo (sección 3.14 y sección [[2026-08-11-2 Actividad Docker k8s minikube#5. Levantar el clúster con el driver de Docker|5 de la actividad]]), pero **no lo elimina**: todo el disco del "nodo" queda guardado tal cual estaba, incluida la imagen `notes-api:k8s` que cargamos. Lo confirmamos con:

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

> Si en algún momento querés liberar por completo el espacio en disco que usa minikube (por ejemplo, se te quedó sin espacio la máquina), la opción es `minikube delete` en lugar de `minikube stop`. Pero ojo: `delete` borra el nodo entero, incluida la imagen que cargamos — la próxima vez habría que repetir `minikube start` **y** `minikube image load notes-api:k8s` (secciones [[2026-08-11-2 Actividad Docker k8s minikube#5. Levantar el clúster con el driver de Docker|5]] y [[2026-08-11-2 Actividad Docker k8s minikube#6. Pasar nuestra imagen al clúster de minikube|6]] de la actividad) antes de poder hacer `kubectl apply` de nuevo. Para "pausar y seguir mañana", `minikube stop` es lo correcto.

### 5.3 Detener el contenedor Docker de la sección 2

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

### 5.4 Cómo levantar todo de nuevo

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

Si en cambio en algún momento usaste `minikube delete`, tenés que reconstruir la imagen si cambiaste código (`docker build -t notes-api:k8s .`, sección [[2026-08-11-2 Actividad Docker k8s minikube#3. Reconstruir la imagen Docker|3 de la actividad]]) y volver a cargarla en el clúster nuevo (`minikube image load notes-api:k8s`, sección [[2026-08-11-2 Actividad Docker k8s minikube#6. Pasar nuestra imagen al clúster de minikube|6 de la actividad]]) antes del `kubectl apply -f k8s/`.
