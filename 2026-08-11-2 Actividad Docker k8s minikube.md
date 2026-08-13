# Actividad 2026-08-11: Deployment de 3 instancias de `notes-api` en Kubernetes

Continuación de [2026-08-11 Docker y Fundamentos de Kubernetes](2026-08-11%20Docker%20y%20Fundamentos%20de%20Kubernetes.md) — acá se separó la actividad práctica del apunte teórico de esa clase.

Enunciado de la actividad:

> Escribir un manifest de k8s que declare un Deployment con 3 instancias de la aplicación de notas. Cada instancia debe tener un parámetro distinto en el título del API, la web inicial, o el parámetro de health. Este debe ser especificado mediante un ConfigMap. Instalar minikube e iniciar el deployment con `kubectl`.

No te preocupes si algo no te cierra a la primera lectura: la idea de esta sección es que entiendas el *por qué* de cada decisión, no solo copiar comandos.

## 1. Antes de arrancar: una trampita del enunciado

El enunciado pide "un Deployment con 3 instancias" pero también que "cada instancia tenga un parámetro distinto". Estas dos frases, leídas juntas, esconden un malentendido muy común cuando uno recién está aprendiendo Kubernetes.

Repasá la sección [3.6 Deployment](2026-08-11%20Docker%20y%20Fundamentos%20de%20Kubernetes.md#36-deployment) del apunte de Docker y Kubernetes: un Deployment tiene **un solo** `spec.template` (la "receta" del Pod), y `spec.replicas` le dice a Kubernetes cuántas copias **idénticas** de esa receta tiene que mantener corriendo. Es decir, si vos hacés **un** Deployment con `replicas: 3`, Kubernetes te va a crear 3 Pods clonados a partir del mismo template — con el mismo ConfigMap, las mismas variables de entorno, todo igual. No hay forma de que el Pod 1 reciba un valor de ConfigMap distinto al Pod 2 si ambos salen del mismo Deployment, porque el Deployment no sabe "diferenciar" sus propias réplicas entre sí.

Entonces, ¿cómo logramos que cada instancia tenga una configuración distinta? La solución es crear **3 Deployments separados**, cada uno con `replicas: 1`, y cada uno apuntando a **su propio ConfigMap**. Cada Deployment es una "instancia" de la aplicación con su propia identidad y su propia configuración; entre los tres suman las 3 instancias que pide el enunciado. Es un poco más de YAML para escribir, pero es la única forma correcta de lograr esto con las piezas que ya conocemos (Deployment + ConfigMap).

## 2. Preparar la app para que lea su configuración desde variables de entorno

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
- `HEALTH_STATUS` es el **parámetro de health**. Como la app original no tenía ningún endpoint de salud, se agregó `GET /health`, que es el patrón estándar que usan los orquestadores (incluido Kubernetes, con sus `livenessProbe`/`readinessProbe` de la sección [4. Anatomía de un YAML de Deployment](2026-08-11%20Docker%20y%20Fundamentos%20de%20Kubernetes.md#4-anatomía-de-un-yaml-de-deployment-nginx) del apunte de Docker y Kubernetes) para preguntarle a una app "¿estás bien?".
- `INSTANCE_NAME` no lo pide el enunciado explícitamente, pero se agregó para poder confirmar a simple vista, al hacer `curl`, con qué instancia estamos hablando. Es una ayuda para nosotros como desarrolladores/estudiantes, no un requisito de Kubernetes.

Todas usan `os.getenv("X", "default")`: si la variable de entorno no existe, la app igual arranca con un valor por defecto. Esto es una buena práctica — la app no debería romperse si alguien la corre sin Kubernetes.

## 3. Reconstruir la imagen Docker

Como cambiamos el código de la app, la imagen Docker que ya teníamos construida quedó vieja: todavía tiene el `main.py` sin las variables de entorno. Kubernetes no "ve" tu código fuente, solo ve imágenes de contenedor — así que si no reconstruimos la imagen, vamos a estar desplegando la versión anterior sin darnos cuenta.

```bash
cd notes-api
docker build -t notes-api:k8s .
```

Le pusimos el tag `k8s` (en vez de reusar `latest` o el nombre de antes) simplemente para diferenciarla con claridad de la imagen que usamos con `docker run` directo — es una convención prolija, no una obligación.

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

## 4. Instalar minikube

Recordá la sección [3.14 minikube](2026-08-11%20Docker%20y%20Fundamentos%20de%20Kubernetes.md#314-minikube) del apunte de Docker y Kubernetes: `minikube` levanta un clúster de Kubernetes real (control plane + nodo), pero corriendo localmente en tu máquina, pensado para aprender y desarrollar sin depender de un clúster en la nube. En macOS, la forma más simple de instalarlo es con Homebrew:

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

## 5. Levantar el clúster con el driver de Docker

`minikube` necesita algo sobre lo cual correr su "nodo" (que en realidad es un contenedor o una VM que simula ser un nodo completo de Kubernetes). Como ya teníamos Docker Desktop corriendo, usamos el **driver de Docker**: minikube crea un contenedor especial (`kicbase`) que por dentro corre todos los componentes del clúster (`kube-apiserver`, `etcd`, `kubelet`, etc., de la sección [3.3 Componentes de un clúster](2026-08-11%20Docker%20y%20Fundamentos%20de%20Kubernetes.md#33-componentes-de-un-clúster) del apunte de Docker y Kubernetes).

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

## 6. Pasar nuestra imagen al clúster de minikube

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

## 7. Escribir los manifiestos: un ConfigMap + un Deployment por instancia

Ahora sí, la parte central de la actividad. Siguiendo lo que explicamos en la sección 1, se creó una carpeta `notes-api/k8s/` con **tres archivos**, uno por instancia. Cada archivo contiene dos objetos separados por `---` (así es como YAML permite declarar varios documentos en un mismo archivo): un `ConfigMap` y el `Deployment` que lo consume.

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
# queda desacoplado de las otras dos instancias (ver sección 1: un solo
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
- **`replicas: 1`**: cada Deployment es una sola instancia, como definimos en la sección 1. Si quisiéramos que la "instancia 1" tuviera alta disponibilidad, podríamos subir esto a 2 o 3 — pero ojo, esas réplicas adicionales seguirían compartiendo la configuración de `notes-api-config-1`, siempre según lo explicado antes.
- **`selector.matchLabels` y `template.metadata.labels` incluyen `instance: instancia-1`**, no solo `app: notes-api`. Esto es fundamental: si los tres Deployments usaran como selector únicamente `app: notes-api`, los tres intentarían "adoptar" los mismos Pods (los de las otras instancias también matchean esa label), y Kubernetes tira un error de validación porque un Deployment no puede tener un selector que se superponga con el de otro. Agregar `instance: instancia-N` como parte de la label y del selector evita esa colisión y, de paso, nos deja identificar de un vistazo a qué instancia pertenece cada Pod con `kubectl get pods --show-labels`.
- **`imagePullPolicy: IfNotPresent`**: le dice a Kubernetes "si ya tenés esta imagen localmente (en este caso, porque la cargamos con `minikube image load`), usala tal cual; no intentes bajarla de ningún registro". Sin esto, el valor por defecto de Kubernetes para imágenes sin un tag `latest` también es `IfNotPresent`, pero dejarlo explícito documenta la intención y evita sorpresas.

## 8. Aplicar los manifiestos con `kubectl`

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

Notá que `kubectl` reporta la creación de **6 objetos**: 3 ConfigMaps + 3 Deployments — coherente con la decisión de la sección 1 de usar un Deployment por instancia en vez de uno solo con `replicas: 3`.

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

## 9. Confirmar que cada instancia realmente tiene su propia configuración

Falta la prueba de fuego: verificar que el ConfigMap efectivamente cambió el comportamiento de cada Pod. Como estos Pods todavía no tienen un `Service` que los exponga (ver sección [3.7 Service](2026-08-11%20Docker%20y%20Fundamentos%20de%20Kubernetes.md#37-service) del apunte de Docker y Kubernetes — acá optamos por no agregar uno para no sumar complejidad a una actividad que ya tiene varias piezas nuevas), usamos `kubectl port-forward` para abrir un túnel temporal desde un puerto de nuestra máquina hacia el puerto 8000 de cada Deployment:

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

## 10. Comandos útiles para inspeccionar

```bash
# Ver a qué instancia pertenece cada pod
kubectl get pods --show-labels

# Ver el detalle de un Deployment puntual (eventos, imagen usada, réplicas)
kubectl describe deployment notes-api-deployment-1

# Ver el contenido de un ConfigMap
kubectl describe configmap notes-api-config-1
```

> Para bajar todo lo que levantamos en esta actividad (y volver a levantarlo después), ver la sección [5. Finalmente, podemos bajar todos los servicios](2026-08-11%20Docker%20y%20Fundamentos%20de%20Kubernetes.md#5-finalmente-podemos-bajar-todos-los-servicios) del apunte de Docker y Kubernetes.

## 11. Resumen del recorrido

1. Nos dimos cuenta de que "3 instancias con configuración distinta" en realidad requiere **3 Deployments** (uno por instancia), no un único Deployment con `replicas: 3` — porque todas las réplicas de un mismo Deployment son clones idénticos.
2. Modificamos `notes-api/main.py` para que el título, el mensaje inicial y el estado de health salgan de variables de entorno en vez de estar *hardcodeados*.
3. Reconstruimos la imagen Docker (`docker build`) porque el código cambió.
4. Instalamos minikube y levantamos un clúster local de Kubernetes con `minikube start --driver=docker`.
5. Cargamos la imagen construida localmente adentro del clúster con `minikube image load`, porque el Docker del host y el Docker interno de minikube no comparten imágenes automáticamente.
6. Escribimos un `ConfigMap` + `Deployment` por instancia, usando `envFrom.configMapRef` para inyectar la configuración y labels distintas (`instance: instancia-N`) para que los selectores no colisionen entre Deployments.
7. Aplicamos todo con `kubectl apply -f k8s/` y confirmamos con `kubectl get` que los tres Pods estaban `Running`.
8. Verificamos con `kubectl port-forward` + `curl` que cada instancia efectivamente respondía con su propia configuración.
