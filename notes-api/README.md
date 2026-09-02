# notes-api

API en FastAPI para guardar notas, usada como app base a lo largo del curso. Persiste las notas en `data/notes.json`. Expone `GET /`, `POST /add/{note}`, `GET /list` y `GET /health`; el título, el mensaje de bienvenida y el estado de health son configurables por variables de entorno (`API_TITLE`, `WELCOME_MESSAGE`, `HEALTH_STATUS`, `INSTANCE_NAME`).

## Opción A: correr local (sin Docker)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

```bash
curl -s http://localhost:8000/
curl -s -X POST http://localhost:8000/add/comprar-cafe
curl -s http://localhost:8000/list
curl -s http://localhost:8000/health
```

## Opción B: correr con Docker

```bash
docker build -t notes-api .
docker run -d \
  --name notes-api-container \
  -p 8000:8000 \
  -v notes-data:/app/data \
  notes-api
```

```bash
curl -s http://localhost:8000/
curl -s -X POST http://localhost:8000/add/comprar-cafe
curl -s http://localhost:8000/list
```

```bash
docker logs -f notes-api-container
docker stop notes-api-container
docker rm notes-api-container
```

## Opción C: 3 instancias en Kubernetes (minikube), cada una con su ConfigMap

```bash
docker build -t notes-api:k8s .
minikube start --driver=docker
minikube image load notes-api:k8s
kubectl apply -f k8s/
```

```bash
kubectl get pods -o wide
kubectl get deployments
kubectl get configmaps
```

Exponer cada instancia en un puerto local distinto:

```bash
kubectl port-forward deployment/notes-api-deployment-1 8001:8000 &
kubectl port-forward deployment/notes-api-deployment-2 8002:8000 &
kubectl port-forward deployment/notes-api-deployment-3 8003:8000 &
```

```bash
curl -s http://localhost:8001/
curl -s http://localhost:8002/
curl -s http://localhost:8003/
```

Apagar todo:

```bash
kill %1 %2 %3 2>/dev/null   # o: pkill -f "kubectl port-forward"
kubectl delete -f k8s/
minikube stop
```
