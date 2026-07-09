FROM splunk/splunk:10.4.1

USER root
COPY --chown=999:999 apps/incident_platform /opt/incident_platform_seed
COPY --chown=999:999 docker-entrypoint-with-app.sh /usr/local/bin/docker-entrypoint-with-app.sh
RUN chmod 755 /usr/local/bin/docker-entrypoint-with-app.sh

USER 999
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-with-app.sh"]
CMD ["start-service"]
