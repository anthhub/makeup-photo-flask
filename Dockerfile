FROM ubuntu:18.04

RUN apt-get update &&  apt-get -y install ca-certificates python3.6 python3-pip git &&\ 
    apt-get clean && rm -rf /var/lib/apt/lists/*  && mkdir -p /root/.pip
COPY cartoon  /app/cartoon   
COPY makeup  /app/makeup   
COPY strUtil.py /app
COPY app.py /app
COPY pip.conf /root/.pip/pip.conf    
COPY requirements.txt /app/requirements.txt

RUN pip3 install -r /app/requirements.txt
WORKDIR /app

EXPOSE 8000 5000

CMD ["python", "/app/app.py"]



