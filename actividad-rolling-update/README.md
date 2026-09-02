# Actividad: Rolling Update

Despliegue de `notes-api` en Kubernetes (minikube) usando la estrategia por defecto de un `Deployment`: **rolling update**. Un solo Deployment/Service pasa de la imagen `v1` a `v2` reemplazando el Pod de a poco, con posibilidad de ver el historial y hacer rollback.

## 1. Construir las imágenes

```bash
docker build --build-arg APP_VERSION=v1 -t notes-api:v1 .
docker build --build-arg APP_VERSION=v2 -t notes-api:v2 .
```

## 2. Levantar minikube y cargar las imágenes

```bash
minikube start --driver=docker
minikube image load notes-api:v1
minikube image load notes-api:v2
```

## 3. Deploy

```bash
kubectl apply -f k8s/deployment.yaml
kubectl rollout status deployment/notes-api
```

## 4. Probar v1

```bash
kubectl port-forward service/notes-api 8000:8000 &
curl -s http://localhost:8000/
curl -s http://localhost:8000/version
curl -s -X POST http://localhost:8000/add/comprar-pan
curl -s http://localhost:8000/list
curl -s http://localhost:8000/health
```

## 5. Hacer el rolling update a v2

```bash
kubectl set image deployment/notes-api notes-api=notes-api:v2
kubectl rollout status deployment/notes-api
```

Ver que el pod nuevo entra antes de matar el viejo:

```bash
kubectl get pods
```

## 6. Probar v2

Reabrir el túnel (el anterior queda apuntando al pod viejo) y probar:

```bash
kill %1 2>/dev/null   # o: pkill -f "kubectl port-forward"
kubectl port-forward service/notes-api 8000:8000 &

curl -s http://localhost:8000/
curl -s http://localhost:8000/version
curl -s http://localhost:8000/health
curl -s http://localhost:8000/list
curl -s -X POST http://localhost:8000/add/comprar-jabon
```

## 7. Historial y rollback

```bash
kubectl rollout history deployment/notes-api
kubectl rollout undo deployment/notes-api
```

Reabrir el túnel y confirmar que volvió a v1:

```bash
kill %1 2>/dev/null   # o: pkill -f "kubectl port-forward"
kubectl port-forward service/notes-api 8000:8000 &
curl -s http://localhost:8000/version
```

## Apagar todo

```bash
pkill -f "kubectl port-forward"
kubectl delete -f k8s/deployment.yaml
minikube stop
```
