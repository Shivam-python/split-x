FROM python:3.9
ENV PYTHONUNBUFFERED 1

RUN mkdir /aplitwise
WORKDIR /splitwise

COPY requirements.txt /splitwise/

RUN pip install -r requirements.txt
COPY . /splitwise/

EXPOSE 8000

# command to run
CMD ["python","manage.py","runserver","0.0.0.0:8000"]