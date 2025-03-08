
<img src="https://i.postimg.cc/Hxc2TQDV/Asset-2.png" alt="Asset-2" width="300" height="200">
# Intelligent Logging Solution

We designed a simple yet efficient logging solution using Fluentbit to simplify log collection, processing, and forwarding. 

## System  
My current setup on which I am running this logging solution:  

- **Device:** Apple M4 Max  
- **RAM:** 36 GB  
- **macOS Version:** 15.3.1 (24D70)  

### Minimum Requirements
- **OS**: Linux , macOS, or Windows  
- **Docker**: Installed 
- **Fluentbit**: Installed and configured  
- **Nginx**: Installed (if required for log forwarding or UI)  
## Technology

We use these tools to develop this solution:

[![Docker](https://img.shields.io/badge/docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)][Docker-url]  
[![Fluentbit](https://img.shields.io/badge/fluent--bit-800080?style=for-the-badge&logo=fluentbit&logoColor=white)][FluentBit-url]  
[![Nginx](https://img.shields.io/badge/nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)][Nginx-url]  
[![Docker Compose](https://img.shields.io/badge/docker%20compose-000000?style=for-the-badge&logo=docker&logoColor=white)][DockerCompose-url]  

[Docker-url]: https://www.docker.com  
[Fluentbit-url]: https://fluentbit.io/  
[DockerCompose-url]: https://docs.docker.com/compose/  
[Nginx-url]: https://nginx.org/  
## Deployment

To start all containers at once, use:
```bash
  docker-compose up --build
```
This command will immediately create and start four containers—one for Fluentbit and the others for logs. 




You can check the running containers and their exposed ports using the following command
```bash
  docker ps 
```
This will list all active containers along with their port mappings.

To access a containerized application in your browser, use:
```bash 
localhost:[PORT]
```
Replace [PORT] with the actual port number mapped to the container.If you're unsure about the port, check the PORTS column in the docker ps output.

To check logs for all containers, open three different terminals and run:
```bash 
ab -n 100 -c 10 http://localhost:[PORT]/
```
Replace [PORT] with the actual port of the container you want to test.

Check the logs using 🚀
```bash 
docker logs [CONTAINER_ID]
```

Enjoy monitoring your logs in real time 🎉

### Note:
If you are on Mac, the ```ab```command runs directly without additional installation.

If you are using Windows WSL or Linux, you need to install Apache Benchmark (ab) first:

Install ```ab``` on Linux/WSL:
```bash 
sudo apt update && sudo apt install apache2-utils -y
```













