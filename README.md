![Logo](https://i.postimg.cc/0jsnDzcZ/Asset-1.png)

# Intelligent Logging Software

We designed a simple yet efficient logging solution using Fluentbit to simplify log collection, processing, and forwarding. 
## Current Architecture
#### Reconfigure the setup. It needs to be run again.

- Fluent Bit collects logs from cluster.
- Sends logs to Kafka.
- Alloy processes and transforms the logs from kafka.
- Alloy Forwards logs to Loki.
- Loki stores logs as indexes and chunks in MinIO.
- Grafana visualizes the logs from Loki.

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

![Kafka](https://img.shields.io/badge/kafka-231F20?style=for-the-badge&logo=apache-kafka&logoColor=white)

[![Grafana](https://img.shields.io/badge/grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)][Grafana-url] 

![Loki](https://img.shields.io/badge/loki-000000?style=for-the-badge&logo=grafana&logoColor=white)

[Docker-url]: https://www.docker.com  
[Fluentbit-url]: https://fluentbit.io/  
[DockerCompose-url]: https://docs.docker.com/compose/  
[Nginx-url]: https://nginx.org/  
[Kubernetes-url]: https://kubernetes.io/  
[Grafana-url]: https://grafana.com/  
[Loki-url]: https://grafana.com/oss/loki/  
[Kafka-url]: https://kafka.apache.org/


## Configuration
The purpose of using a KIND cluster is to deploy Kubernetes in a local environment. Docker is required to run a KIND cluster. If you already have a Kubernetes cluster, there is no need to deploy a KIND cluster.

#### Set Permissions for the Installation Script
```bash
 chmod 777 /KindCluster/install_kind.sh
 ```
#### Install KIND 
```bash
 ./KindCluster/install_kind.sh # For Linux 

[ $(uname -m) = x86_64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.28.0/kind-darwin-amd64 # For Intel Mac

[ $(uname -m) = arm64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.28.0/kind-darwin-arm64 # For M1 / ARM Mac

chmod +x ./kind
 ```
#### Install kubectl 
```bash
brew install kubectl # For Mac
```
For setting up kubectl on Linux, follow this [tutorial](https://medium.com/cypik/installing-and-setting-up-kubectl-on-linux-or-ubuntu-37fe99623f8e) 
#### Verify the Installation of KIND and kubectl 
```bash
kubectl version
 ./kind --version  # For Mac
kind --version # For Linux
 ```
#### Configure Control Plane and Worker Nodes
```bash
./kind create cluster --name=mycluster --config=./KindCluster/config.yaml # For Mac
kind create cluster --name=mycluster --config=./KindCluster/config.yaml # For Linux
```
#### Check the Nodes
```bash
kubectl get nodes
```
#### Install Rosetta 2 
```bash
softwareupdate --install-rosetta --agree-to-license # For M1 / ARM Mac
```
#### Enable binfmt support with Docker's buildx 
```bash
docker run --privileged --rm tonistiigi/binfmt --install all # For M1 / ARM Mac
```
#### Verify QEMU is set up correctly 
```bash
docker run --rm --platform linux/amd64 alpine uname -m # For M1 / ARM Mac
```

## Deployment on kubernetes:
#### To configure Nopayloaddb: 
```bash 
cd src/Nopayloaddb
```
#### Create the namespace:
```bash 
kubectl create namespace npps
```
#### Now run Nopayloaddb (wait for the pods to start and run):
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
## Kafka and FluentBit Setup

#### Delete Grafana-Loki Namespace
kubectl delete ns grafana-loki

#### Create Kafka Namespace
```bash
kubectl create ns kafka
```
#### Set Current Context to Kafka Namespace
```bash
kubectl config set-context --current --namespace=kafka
```
#### Create Fluent Bit Service Account
```bash
cd fluentbit
```
```bash
kubectl create -f cluster-role.yaml -f clusterrole-binding.yaml -f service-account.yaml
```
#### Deploy Fluent Bit
```bash
kubectl create -f fluent-bit-configmap.yaml
kubectl create -f fluent-bit-daemonset.yaml
```
#### Deploy Kafka 
```bash
cd ..
cd kafka
```
```bash
kafka create -n kafka -f kafka-pvc.yaml -f kafka-statefulset.yaml -f kafka-service.yaml
```
#### Deploy Kafka UI
```bash
helm install kafka-ui kafka-ui/kafka-ui --values kafka-ui.yaml
```
#### Access Kafka UI
```bash 
kubectl port-forward svc/kafka-ui 8081:80
```
Open your browser and navigate to:
http://localhost:8080

#### In Kafka User Interface:

- Go to Topics

- Click on ops.kube-logs-fluentbit.stream.json.001

- View Messages (logs)

We can now access logs from Nopayloaddb 

## Deploy Alloy, Loki and Grafana
Configuring alloy which are acting as a consumer of kafka and get logs from kafka. and then sends logs to loki.
```bash
cd ..
cd loki
```
#### Create Namespace
```bash
k create ns monitoring
```
#### Sets your current kubectl context to use the monitoring namespace
```bash
kubectl config set-context --current --namespace=monitoring
```
#### Create Persistent Volume Claim
```bash
k create -f loki-pvc.yaml
```
#### Installation of Alloy, Loki and Grafana using Helm
```bash
helm repo add grafana https://grafana.github.io/helm-chart

helm upgrade --install --values loki-grafana.yaml loki grafana/loki-stack -n monitoring
```
```bash
helm upgrade --install alloy grafana/alloy -n monitoring --values configalloy.yaml
```
#### Get the Username and Password for Grafana UI
```bash
kubectl get secret loki-grafana -n grafana-loki -o jsonpath="{.data.admin-user}" | base64 --decode
```
```bash
kubectl get secret loki-grafana -n grafana-loki -o jsonpath="{.data.admin-password}" | base64 --decode
```
Then go to Connections > Data sources, select Loki and go to Explore to show the logs of the payload.


## Min IO setup
Loki sends logs to MinIO for storing log indexes and chunks.
 
```bash
cd ..
cd minio
```
#### Creates a new namespace called minio
```bash
k create ns mino
```
#### Sets your current kubectl context to use the minio namespace
```bash
kubectl config set-context --current --namespace=minio
```
#### Deploys MinIO
```bash
k create -f minio-newdeploy.yaml -f minio-service.yaml -f minio-pvc.yaml -f minio-secret.yaml
```
#### to expose port locally on your machine
```bash
 k port-forward svc/minio-service 9090:9090 -n minio
```
 Open the MinIO web UI by visiting http://localhost:9090 and create a bucket named logs. You will then see the logs stored as indexes and chunks.

 By default, the username and password of the MinIO UI are minioadmin. We will replace them using Kubernetes secrets.





