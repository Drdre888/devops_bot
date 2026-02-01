FROM postgres:15
COPY setup-replication.sh /docker-entrypoint-initdb.d/

RUN chmod +x /docker-entrypoint-initdb.d/setup-replication.sh

RUN echo "hot_standby = on" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "log_replication_commands = on" >> /usr/share/postgresql/postgresql.conf.sample

EXPOSE 5432
