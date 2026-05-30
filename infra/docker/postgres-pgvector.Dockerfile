ARG POSTGRES_BASE_IMAGE=postgres:18-alpine
FROM ${POSTGRES_BASE_IMAGE} AS builder

ARG PGVECTOR_REF=master

RUN apk add --no-cache build-base git postgresql-dev

WORKDIR /tmp
RUN git clone --depth 1 --branch "${PGVECTOR_REF}" https://github.com/pgvector/pgvector.git

WORKDIR /tmp/pgvector
RUN make with_llvm=no && make install with_llvm=no

FROM ${POSTGRES_BASE_IMAGE}

COPY --from=builder /usr/local/lib/postgresql/vector.so /usr/local/lib/postgresql/vector.so
COPY --from=builder /usr/local/share/postgresql/extension/vector* /usr/local/share/postgresql/extension/
