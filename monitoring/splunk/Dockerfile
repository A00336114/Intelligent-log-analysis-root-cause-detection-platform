FROM splunk/splunk:10.4.1

USER root
COPY --chown=splunk:splunk apps/incident_platform /opt/incident_platform_seed
COPY --chown=splunk:splunk docker-entrypoint-with-app.sh /usr/local/bin/docker-entrypoint-with-app.sh
RUN mkdir -p \
      /opt/splunk/var/log/splunk \
      /opt/splunk/var/log/introspection \
      /opt/splunk/var/log/watchdog \
      /opt/splunk/var/log/client_events \
    && chown -R splunk:splunk /opt/splunk/var/log \
    && chmod 755 /usr/local/bin/docker-entrypoint-with-app.sh

USER 999
HEALTHCHECK --interval=30s --timeout=30s --start-period=180s --retries=5 \
  CMD curl -k --max-time 10 -s -o /dev/null -w "%{http_code}" https://localhost:8089/services/server/info | grep -Eq "^(200|401)$" || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint-with-app.sh"]
CMD ["start-service"]
