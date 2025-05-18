
# Intelligent Logging Software

We designed a simple yet efficient logging solution using Fluentbit to simplify log collection, processing, and forwarding. 

## System  
My current setup on which I am running this logging solution:  

- **Device:** Apple M4 Max  
- **RAM:** 36 GB  
- **macOS Version:** 15.3.1 (24D70)  

### Minimum Requirements
- **OS**: Linux , macOS, or Windows  
- **Docker**: Installed 
- **Kubernetes Cluster**: Installed
- **Grafana and Loki**: Installed
- **Helm**: Installed
- **Fluentbit**: Installed and configured  

## Technology

We use these tools to develop this solution:

[![Kubernetes](https://img.shields.io/badge/kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)][Kubernetes-url] 

[![Fluentbit](https://img.shields.io/badge/fluent--bit-800080?style=for-the-badge&logo=fluentbit&logoColor=white)][FluentBit-url] 

[![Grafana](https://img.shields.io/badge/grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)][Grafana-url] 

![Loki](https://img.shields.io/badge/loki-000000?style=for-the-badge&logo=grafana&logoColor=white)

[Docker-url]: https://www.docker.com  
[Fluentbit-url]: https://fluentbit.io/  
[DockerCompose-url]: https://docs.docker.com/compose/  
[Nginx-url]: https://nginx.org/  
[Kubernetes-url]: https://kubernetes.io/  
[Grafana-url]: https://grafana.com/  
[Loki-url]: https://grafana.com/oss/loki/  

## Deployment on kubernetes:
#### To configure Nopayloaddb: 
```bash 
cd src/Nopayloaddb
```
#### Create the namespace:
```bash 
kubectl create namespace npps
```
#### Now run Nopayloaddb:

```bash 
 kubectl create -f secret.yaml -f django-service.yaml -f django-deployment.yaml -f postgres-service.yaml -f postgres-deployment.yaml
```
#### To access it in the browser:
```bash
kubectl port-forward deployment/npdb 8000:8000 -n npps 
```
```bash
http://localhost:8000/api/cdb_rest/payloadiovs/?gtName=sPHENIX_ExampleGT_24&majorIOV=0&minorIOV=999999
```
### Configure Grafana, Loki and FluentBit
#### To install Grafana, Loki and Fluent Bit at once  
```bash 
helm upgrade --install --values all-values.yaml loki grafana/loki-stack -n grafana-loki --create-namespace
```

#### To check the status of pods  
```bash
kubectl get pods -n grafana-loki
```

#### To access Grafana UI
```bash
kubectl port-forward svc/loki-grafana 3939:80 -n grafana-loki
```

#### Get the Username and Password for Grafana UI  
```bash
kubectl get secret loki-grafana -n grafana-loki -o jsonpath="{.data.admin-user}" | base64 --decode
```
```bash
kubectl get secret loki-grafana -n grafana-loki -o jsonpath="{.data.admin-password}" | base64 --decode
```

Then go to Connections > Data sources, select Loki and go to Explore to show the logs of the payload.

## KIND Cluster Setup (Optional)
The purpose of using a KIND cluster is to deploy Kubernetes in a local environment. If you already have a Kubernetes cluster, there is no need to deploy a KIND cluster.Docker is required to run a KIND cluster.

#### Set Permissions for the Installation Script
```bash
 chmod 777 /KindCluster/install_kind.sh
 ```
#### Install KIND and Kubectl (On Linux)
```bash
 ./KindCluster/install_kind.sh
 ```
 #### Install KIND (On Mac) 
```bash
 # For Intel Macs
[ $(uname -m) = x86_64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.28.0/kind-darwin-amd64

# For M1 / ARM Macs
[ $(uname -m) = arm64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.28.0/kind-darwin-arm64
chmod +x ./kind

 ```
#### Install kubectl (On Mac)
```bash
brew install kubectl
 ```
#### Verify the Installation of KIND and kubectl
```bash
 kubectl version
 ./kind --version
 ```
 #### Configure Control Plane and Worker Nodes
```bash
./kind create cluster --name=mycluster --config=./KindCluster/config.yaml
```
#### Check the Nodes
```bash
kubectl get nodes
```








