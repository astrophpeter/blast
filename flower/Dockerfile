FROM mher/flower
USER root
RUN addgroup -S app && adduser -S -G app app
RUN apk add --no-cache bash
USER app
