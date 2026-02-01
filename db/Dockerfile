FROM postgres:15
COPY init.sql /docker-entrypoint-initdb.d/
RUN echo "wal_level = replica" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "max_wal_senders = 3" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "wal_keep_size = 64" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "log_replication_commands = on" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "listen_addresses = '*'" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "host replication all 0.0.0.0/0 md5" >> /usr/share/postgresql/pg_hba.conf.sample && \
    echo "host all all 0.0.0.0/0 md5" >> /usr/share/postgresql/pg_hba.conf.sample
EXPOSE 5432
