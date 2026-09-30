# ==============================================================================
# iperf3 server - Week 05 Lab (Activity 1)
# Minimal Alpine image providing an iperf3 server for TCP/UDP throughput tests.
# ==============================================================================

FROM alpine:3.20

RUN apk add --no-cache iperf3 \
    && adduser -D -H -s /sbin/nologin iperf

USER iperf

EXPOSE 5201/tcp
EXPOSE 5201/udp

ENTRYPOINT ["iperf3"]
CMD ["--server", "--verbose"]
