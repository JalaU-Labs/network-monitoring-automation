# ==============================================================================
# Target host - Week 05 Lab (Activity 2)
# Lightweight Alpine image used as a destination host. Provides iproute2
# so that tc netem can be applied at runtime to simulate latency and loss.
# ==============================================================================

FROM alpine:3.20

RUN apk add --no-cache iproute2 iputils \
    && rm -rf /var/cache/apk/*

# The container stays alive; network shaping is applied via the compose
# `command` field so each target can have its own netem parameters.
CMD ["sleep", "infinity"]
