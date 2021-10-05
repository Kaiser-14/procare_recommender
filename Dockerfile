FROM python:3.8-slim-buster
WORKDIR /app
COPY requirements.txt /app/requirements.txt
# Install dependencies packages
RUN apt update 
RUN  apt upgrade -y 
# RUN  apt install -y curl 
# RUN  apt install -y gnupg2  
# RUN  apt install -y python3 
# RUN  apt install -y python3-pip
RUN  apt install -y libpq-dev
# RUN  apt install -y python3-dev 
# RUN  apt install -y apt-transport-https 
# RUN  apt install -y wget 
RUN  pip3 install --no-cache-dir -r requirements.txt
RUN  apt clean 
RUN  apt autoremove
COPY . /app
# RUN chmod 777 /app/create_networks.sh
# EXPOSE 5005
ENTRYPOINT ["python","/app/app.py"]
