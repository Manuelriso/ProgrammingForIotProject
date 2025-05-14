# set the kernel to use
FROM python:3.8-alpine
# copy all the files in the container

WORKDIR /app


COPY . .
# install the needed requirements

RUN chmod 666 catalog.json

RUN pip3 install -r requirements.txt
# the command that will be executed when the container will start
CMD ["python3","./catalog.py"]