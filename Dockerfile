FROM python:3.6.5-jessie

WORKDIR /usr/src/app

COPY Pipfile.lock ./
RUN pip install pipenv
RUN pipenv install --system

COPY . .

EXPOSE 8080

CMD [ "python", "-m", "boardgame-connector" ]