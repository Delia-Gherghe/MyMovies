FROM python:3.9.7-bullseye
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
ENV FLASK_APP=movies.py
CMD ["flask", "run", "--host=0.0.0.0", "--port=8001"]