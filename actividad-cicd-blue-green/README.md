# Actividad: Blue-Green Deployment + CI/CD

Copia de [actividad-blue-green](../actividad-blue-green) con un pipeline de **GitHub Actions** agregado. Despliegue de `notes-api` en Kubernetes (minikube) usando la estrategia **blue-green**: `v1` (blue) y `v2` (green) corren al mismo tiempo como Deployments separados, y un único `Service` decide a cuál de los dos les manda el tráfico cambiando su `selector`.

## CI: build + push automático a Docker Hub

El workflow [.github/workflows/blue-green-build-push.yml](../.github/workflows/blue-green-build-push.yml) se dispara automáticamente en cada `push` a la branch `dev` que toque esta carpeta. Por cada push:

1. Hace checkout del código.
2. Construye la imagen dos veces (una por cada `APP_VERSION`: `v1` y `v2`), usando este mismo `Dockerfile`.
3. Publica ambas imágenes en Docker Hub como `<usuario>/notes-api-blue-green:v1` / `:v2`, más un tag inmutable con el SHA del commit (`:v1-<sha>` / `:v2-<sha>`) para trazabilidad — ver la sección 8 de [2026-09-01 CI-CD.md](../2026-09-01%20CI-CD.md).

### Configuración necesaria (una sola vez)

En el repo de GitHub, ir a **Settings → Secrets and variables → Actions → New repository secret** y crear:

| Secret | Valor |
|---|---|
| `DOCKERHUB_USERNAME` | Tu usuario de Docker Hub |
| `DOCKERHUB_TOKEN` | Un *Access Token* de Docker Hub (Docker Hub → Account Settings → Security → New Access Token; **no** uses tu contraseña) |

Sin estos dos secrets configurados, el job falla en el paso `Log in to Docker Hub`.

## Uso local (manual, igual que antes)

### 1. Construir las imágenes

```bash
docker build --build-arg APP_VERSION=v1 -t notes-api:v1 .
docker build --build-arg APP_VERSION=v2 -t notes-api:v2 .
```

### 2. Levantar minikube y cargar las imágenes

```bash
minikube start --driver=docker
minikube image load notes-api:v1
minikube image load notes-api:v2
```

### 3. Deploy inicial (solo blue + el Service apuntando a blue)

```bash
kubectl apply -f k8s/deployment-blue.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/notes-api-blue
```

Verificar que el Service apunta a blue y corre la imagen v1:

```bash
kubectl get service notes-api -o jsonpath='{.spec.selector.version}'
kubectl get pods -l version=blue -o jsonpath='{.items[0].spec.containers[0].image}'
```

### 4. Desplegar green junto a blue

Green queda corriendo, pero blue sigue sirviendo el tráfico (todavía no se tocó el Service):

```bash
kubectl apply -f k8s/deployment-green.yaml
kubectl rollout status deployment/notes-api-green
```

### 5. Cambiar el tráfico de blue a green

```bash
kubectl patch service notes-api -p '{"spec":{"selector":{"version":"green"}}}'
```

Verificar que el Service quedó apuntando a green y corre la imagen v2:

```bash
kubectl get service notes-api -o jsonpath='{.spec.selector.version}'
kubectl get pods -l version=green -o jsonpath='{.items[0].spec.containers[0].image}'
```

### 6. Rollback instantáneo

Sin tocar pods, solo vuelve a apuntar el Service a blue:

```bash
kubectl patch service notes-api -p '{"spec":{"selector":{"version":"blue"}}}'
kubectl get service notes-api -o jsonpath='{.spec.selector.version}'
```

### 7. Confirmar green y limpiar blue

Una vez confirmado que green está bien, cortar definitivamente el tráfico hacia blue y eliminarlo:

```bash
kubectl patch service notes-api -p '{"spec":{"selector":{"version":"green"}}}'
kubectl delete -f k8s/deployment-blue.yaml
```

### Comandos útiles

```bash
kubectl get pods -o wide --show-labels
kubectl get deployments
kubectl get services
```

### Apagar todo

```bash
kubectl delete -f k8s/deployment-green.yaml
kubectl delete -f k8s/service.yaml
minikube stop
```
