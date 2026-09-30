# network-monitoring-automation

Laboratorio Semana 5 - Redes de Computadoras 2 (CSNT-245)
Jala University | Ingeniería de Software | Cohorte 5

**Autor:** Diego Alejandro Botina

---

## 1. Introducción

Este repositorio contiene la solución completa del laboratorio de la Semana 5.
El objetivo es **diseñar, implementar y analizar** un sistema básico de gestión
de red que combina tres componentes:

1. Monitoreo de conectividad, latencia y rendimiento con herramientas reales
   (`ping`, `traceroute`, `iperf3`, `mtr`).
2. Automatización de tareas de diagnóstico mediante un script en Python.
3. Simulación de una red controlada mediante Docker, incluyendo la
   introducción de condiciones adversas (latencia y pérdida de paquetes) con
   `tc netem`.

El diseño sigue un enfoque DevOps: infraestructura como código, ejecución
reproducible con `uv`, contenedores Docker y pruebas automatizadas con `pytest`.

---

## 2. Arquitectura general del sistema

La red virtual `netmon-net` (subred `172.28.0.0/24`) aloja cinco contenedores:

```
                    +-------------------------------------------+
                    |              netmon-net                   |
                    |           172.28.0.0/24                   |
                    |                                           |
   +----------+     |   +---------------+   +---------------+   |
   |  Host    |     |   | target-alpha  |   | target-beta   |   |
   |  Arch    |<----+-->| 172.28.0.10   |   | 172.28.0.11   |   |
   | (admin)  |     |   | netem:        |   | netem:        |   |
   +----------+     |   |  delay 50ms   |   |  delay 10ms   |   |
                    |   |  loss 5%      |   |  (sin loss)   |   |
                    |   +---------------+   +---------------+   |
                    |                                           |
                    |   +---------------+   +---------------+   |
                    |   |   monitor     |   | iperf3-server |   |
                    |   | 172.28.0.20   |   | 172.28.0.2    |   |
                    |   | Python 3.14   |   | iperf3 daemon |   |
                    |   | uv + iputils  |   | puerto 5201   |   |
                    |   +---------------+   +---------------+   |
                    +-------------------------------------------+
```

**Roles:**

| Contenedor | IP | Rol |
|---|---|---|
| `netmon-monitor` | `172.28.0.20` | Ejecuta el script de monitoreo (ICMP periódico). |
| `netmon-target-alpha` | `172.28.0.10` | Host destino degradado (delay 50ms + 5% loss). |
| `netmon-target-beta` | `172.28.0.11` | Host destino con latencia leve (10ms). |
| `netmon-iperf3` | `172.28.0.2` | Servidor `iperf3` para las pruebas TCP/UDP de Actividad 1. |
| Host Arch (admin) | — | Ejecuta `ping`, `traceroute`, `mtr`, `iperf3` cliente y Docker. |

**Flujo de datos:**

1. El script de monitoreo dentro de `netmon-monitor` emite `ping` a cada
   host de la configuración.
2. Cada `ping` produce un `ProbeResult` tipado que se agrega en
   `HostStatistics`.
3. Al final de la sesión, los generadores de reporte producen tres archivos
   (JSON, log, Markdown) en `reports/` (volumen montado al host).

---

## 3. Estructura del proyecto

```text
network-monitoring-automation/
├── assets/
│   └── evidence/
│       ├── activity-1/         # Capturas de Actividad 1
│       └── activity-2/         # Capturas de Actividad 2
├── docker/
│   ├── iperf3/Dockerfile       # Servidor iperf3 (Actividad 1)
│   ├── monitor/Dockerfile      # Host de monitoreo (Python 3.14 + uv)
│   └── target/Dockerfile       # Hosts destino (iproute2 para tc netem)
├── docs/
│   └── activity-1-monitoring.md
├── reports/                    # Reportes generados (ignorados por git)
├── scripts/
│   ├── __init__.py
│   ├── config.py               # Carga y validación de config.yaml
│   ├── config.yaml             # Configuración de la sesión de monitoreo
│   ├── models.py               # Modelos de dominio tipados
│   ├── network_monitor.py      # Orquestador / CLI
│   ├── probe.py                # Motor de sondeo ICMP
│   └── report.py               # Generadores JSON, log y Markdown
├── tests/
│   ├── fixtures/               # Configs YAML válidas e inválidas
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_probe.py
│   ├── test_report.py
│   └── test_smoke.py
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## 4. Requisitos previos

- **Sistema operativo:** Linux (probado en Arch Linux).
- **Python 3.14** (gestionado por `uv`, no requiere instalación manual).
- **`uv` 0.12+** ([instalación](https://docs.astral.sh/uv/)).
- **Docker Engine 24+** con `docker compose` v2.
- **`iperf3`, `traceroute`, `mtr`** en el host (solo para Actividad 1):
  ```bash
  sudo pacman -S --needed iperf3 traceroute mtr
  ```
- **GNU Make** (para los atajos del Makefile).

---

## 5. Instalación y puesta en marcha

```bash
# 1. Clonar el repositorio
git clone <URL-del-repositorio>
cd network-monitoring-automation

# 2. Crear el entorno virtual e instalar dependencias
make setup

# 3. Verificar el entorno
make lint
make test

# 4. Construir las imágenes Docker
make docker-build

# 5. Levantar la red y los contenedores
make docker-up

# 6. Ejecutar la sesión de monitoreo dentro del contenedor
make docker-monitor

# 7. Corregir el ownership de los reportes generados
make docker-clean-reports

# 8. Bajar el entorno
make docker-down
```

---

## 6. Actividad 1 — Monitoreo de redes

La documentación completa (herramientas, comandos, resultados y análisis) se
encuentra en [`docs/activity-1-monitoring.md`](docs/activity-1-monitoring.md).

**Resumen de resultados:**

| Prueba | Destino | Métrica clave | Valor |
|---|---|---|---|
| `ping` | `172.28.0.2` | RTT avg | 0.102 ms |
| `ping` | `1.1.1.1` | RTT avg / mdev | 65.229 ms / 78.98 ms |
| `traceroute` | `172.28.0.2` | Saltos | 1 |
| `traceroute` | `1.1.1.1` | Saltos visibles | 1 (resto filtra ICMP) |
| `iperf3` TCP | `172.28.0.2` | Throughput | 73.8 Gbps (0.00005% Retr) |
| `iperf3` UDP (50 Mbps) | `172.28.0.2` | Pérdida / Jitter | 0% / 0.008 ms |
| `iperf3` UDP (1 Gbps) | `172.28.0.2` | Pérdida | 0.42% |
| `mtr` | `1.1.1.1` | Hops / Loss final | 5 / 0% |
| `mtr` | `172.28.0.2` | Hops / Avg | 1 / 0.2 ms |

Herramienta alternativa documentada: **`mtr`** (combina `ping` + `traceroute` con
estadísticas acumuladas por salto).

---

## 7. Actividad 2 — Automatización y gestión centralizada

### 7.1. Diseño del sistema de monitoreo

| Elemento | Definición |
|---|---|
| **Hosts monitoreados** | `target-alpha`, `target-beta`, `cloudflare-dns` |
| **Métricas recolectadas** | Latencia (RTT ICMP), disponibilidad (éxito/fallo de sonda), jitter |
| **Frecuencia** | `interval_seconds: 5` entre rondas |
| **Iteraciones** | `iterations: 10` rondas por host |
| **Timeout por sonda** | `timeout_seconds: 2` |
| **Consolidación** | JSON + log cronológico + reporte Markdown en `reports/` |

La configuración vive en `scripts/config.yaml` y es validada por
`scripts/config.py`. Cualquier valor fuera de rango produce un `ConfigError`
con mensaje explícito.

### 7.2. Automatización con scripting (Python 3.14)

El script se divide en módulos con responsabilidades claras:

- **`scripts/models.py`** — Dataclasses tipadas (`Host`, `MonitoringConfig`,
  `ProbeResult`, `HostStatistics`). `HostStatistics` calcula agregados
  (availability, avg/min/max RTT, jitter) sin efectos secundarios.
- **`scripts/config.py`** — Carga el YAML, valida cada campo y devuelve un
  `MonitoringConfig` inmutable.
- **`scripts/probe.py`** — Ejecuta `ping -c 1 -W <timeout> -n <addr>` vía
  `subprocess.run`, parsea el RTT con una regex y captura `FileNotFoundError`
  y `TimeoutExpired` como `ProbeResult` fallidos (nunca lanza excepción).
- **`scripts/report.py`** — Genera JSON, log y Markdown a partir del mismo
  payload estructurado. Los reportes se escriben con marca de tiempo
  `monitoring-YYYYMMDD-HHMMSS.{json,log,md}`.
- **`scripts/network_monitor.py`** — Orquesta la sesión. CLI con `argparse`,
  soporte para `--config`, `--run-id` y `--version`. Maneja `KeyboardInterrupt`
  retornando código `130` y errores de configuración con código `1`.

**Códigos de salida:**

| Código | Significado |
|---|---|
| `0` | Sesión completada correctamente |
| `1` | Error de configuración |
| `2` | Error inesperado durante la sesión |
| `130` | Interrupción por SIGINT (Ctrl+C) |

### 7.3. Entorno Docker para el monitoreo

- **Red dedicada:** `netmon-net` (subred `172.28.0.0/24`, driver bridge) con
  IPs fijas para determinismo.
- **Host de monitoreo:** `netmon-monitor` (`172.28.0.20`), construido sobre
  `python:3.14-slim-bookworm` con `uv` copiado desde la imagen oficial de
  Astral y `iputils-ping` instalado por `apt`.
- **Hosts destino:** `netmon-target-alpha` (`172.28.0.10`) y
  `netmon-target-beta` (`172.28.0.11`), construidos sobre `alpine:3.20` con
  `iproute2` e `iputils`. Aplican `tc qdisc add dev eth0 root netem ...` al
  arrancar, con `cap_add: [NET_ADMIN]`.
- **Volúmenes:** `./scripts` (read-only) y `./reports` (lectura/escritura) se
  montan en el contenedor del monitor para iteración rápida.

### 7.4. Pruebas realizadas y resultados

**Comando ejecutado:**

```bash
make docker-monitor
```

**Salida del script (10 iteraciones):**

```
[iter   1/10] target-alpha         OK   rtt=101.000 ms
[iter   1/10] target-beta          OK   rtt=20.400 ms
[iter   1/10] cloudflare-dns       OK   rtt=26.600 ms
[iter   2/10] target-alpha         OK   rtt=50.200 ms
[iter   2/10] target-beta          OK   rtt=10.100 ms
[iter   2/10] cloudflare-dns       OK   rtt=29.000 ms
...
[iter   4/10] target-alpha         FAIL rtt=n/a
[iter   4/10] target-beta          OK   rtt=10.100 ms
[iter   4/10] cloudflare-dns       OK   rtt=29.600 ms
...
[iter  10/10] target-alpha         OK   rtt=50.300 ms
[iter  10/10] target-beta          OK   rtt=10.100 ms
[iter  10/10] cloudflare-dns       OK   rtt=30.300 ms

Session summary
---------------
  target-alpha         availability= 90.0%  avg=55.833 ms    jitter=6.462 ms
  target-beta          availability=100.0%  avg=11.170 ms    jitter=1.189 ms
  cloudflare-dns       availability=100.0%  avg=30.660 ms    jitter=6.478 ms
```

**Reportes generados:** `reports/monitoring-*.json`, `.log`, `.md`.

**Evidencias visuales:**

![Topología Docker](../assets/evidence/activity-2/01-docker-topology.png)

![Reglas tc netem](../assets/evidence/activity-2/02-tc-netem.png)

![Sesión de monitoreo](../assets/evidence/activity-2/03-monitoring-session.png)

![Reporte generado](../assets/evidence/activity-2/04-generated-report.png)

### 7.5. Análisis de resultados

- **Degradación artificial detectada:** `target-alpha` con `netem delay 50ms
  loss 5%` mostró exactamente lo esperado: RTT cercano a 50 ms (el delay
  aplicado, sin contar el primer paquete que incluye ARP + encolamiento), una
  pérdida de 1/10 paquetes (10%) y un jitter notablemente mayor que beta
  (6.462 ms vs 1.189 ms). El jitter amplificado no viene del delay en sí, sino
  de la variabilidad que introduce la pérdida en el cálculo de la media.
- **Camino sano:** `target-beta` con `netem delay 10ms` (sin pérdida) exhibió
  100% disponibilidad y un jitter de 1.189 ms, muy inferior al de alpha. Esto
  demuestra que el delay fijo, por sí solo, no degrada la estabilidad; es la
  pérdida lo que rompe la consistencia.
- **Baseline externo:** `cloudflare-dns` (1.1.1.1) promedió 30.66 ms con
  jitter 6.478 ms, coherente con la varianza observada en la Actividad 1. La
  ruta pública tiene más saltos y por tanto más puntos de encolamiento.
- **Detección de fallos:** el script reportó la falla de `target-alpha` en la
  iteración 4 con `error="ping exited with code 1"`. El diseño del `ProbeResult`
  permitió registrar el fallo sin interrumpir la sesión, demostrando tolerancia
  a errores en la automatización.

### 7.6. Acciones de mitigación y escalabilidad

- **Mitigación ante pérdida:** configurar un enlace redundante entre hosts
  críticos (bonding/balanceo). Las métricas recolectadas indican qué hosts
  requieren redundancia (alpha, por su 10% de pérdida).
- **Mitigación ante jitter:** priorización de tráfico mediante QoS (`tc`
  policer + colas HTB) para marcar paquetes sensibles a jitter y encaminarlos
  por una ruta con menor variabilidad.
- **Escalabilidad del monitoreo:** el script soporta N hosts en el YAML. Para
  escalar más allá de decenas de hosts, se propone:
  - Ejecución distribuida con varios `monitor` en diferentes subredes.
  - Reemplazo del backend de almacenamiento de archivos planos por una serie
    temporal (Prometheus + Grafana, InfluxDB).
  - Alertas basadas en umbrales (e.g., `availability < 95%` durante más de
    N sesiones consecutivas).
- **Escalabilidad de la red:** los datos de la sesión sugieren que la topología
  actual (bridge L2) es adecuada para pruebas controladas, pero en producción
  requeriría segmentación en VLANs y agregación LACP entre switches para
  sostener el throughput observado (73.8 Gbps en loopback, no representativo
  de una red real, pero útil como referencia interna).

---

## 8. Preguntas de reflexión

### 8.1. ¿Por qué ICMP es fundamental en la administración de redes?

ICMP es el protocolo de control de la capa de red (RFC 792). A diferencia de
TCP o UDP, no transporta datos de aplicación: transporta información sobre el
estado de la red misma. Es fundamental porque:

- Provee el mecanismo estándar para verificar alcanzabilidad (`Echo
  Request`/`Echo Reply`) sin requerir un servicio de aplicación corriendo en
  el destino.
- Reporta errores de red (`Destination Unreachable`, `Time Exceeded`,
  `Redirect`) que permiten diagnosticar problemas de enrutamiento sin
  inspeccionar el tráfico.
- Es la base de las herramientas de diagnóstico universales: `ping`,
  `traceroute` y `mtr` dependen de ICMP.
- Es ligero y sin estado, lo que lo hace seguro de ejecutar con alta
  frecuencia en producción.

En el laboratorio, ICMP fue la base de toda la Actividad 2: cada sonda es un
par `Echo Request`/`Echo Reply`, y el RTT medido es el tiempo entre ambos.

### 8.2. ¿Qué métricas permiten detectar congestión o degradación del servicio?

| Métrica | Qué mide | Cómo detecta degradación |
|---|---|---|
| **RTT promedio** | Latencia media por paquete | Un aumento sostenido respecto al baseline indica congestión o rutas más largas. |
| **RTT min / max** | Rango de latencias | Un `max` muy superior al `min` indica encolamiento intermitente. |
| **Jitter** | Variabilidad del RTT | Jitter alto (> 30 ms típicamente) degrada VoIP y streaming. |
| **Pérdida de paquetes** | Porcentaje no entregados | Cualquier pérdida > 0% en una red sana es señal de congestión o fallo. |
| **Disponibilidad** | % de sondas exitosas | Cae con interrupciones; útil para SLA. |
| **Throughput** | Bits por segundo efectivos | Cae cuando la red no puede absorber la carga. |

En el laboratorio, `target-alpha` mostró RTT 55.8 ms (vs 11.2 ms de beta),
jitter 6.46 ms (vs 1.19 ms) y pérdida 10% (vs 0% de beta). La combinación de
las tres métricas confirma degradación, y cada una por separado apunta al
mismo diagnóstico: un enlace congestionado o con pérdida introducida.

### 8.3. ¿Qué ventajas aporta la automatización en la gestión de redes?

- **Ejecución periódica sin intervención humana:** las sondas se ejecutan cada
  N segundos automáticamente, permitiendo detectar fallos fuera del horario
  laboral.
- **Consistencia:** todos los hosts se monitorean con los mismos parámetros
  (timeout, iteraciones, formato de salida), eliminando variabilidad manual.
- **Histórico comparable:** los reportes quedan fechados y en formato
  estructurado (JSON), permitiendo análisis de tendencias y comparaciones
  entre sesiones.
- **Detección temprana:** al ejecutarse continuamente, se puede alertar sobre
  degradación antes de que los usuarios la perciban.
- **Escalabilidad operativa:** un solo script monitorea N hosts; añadir uno
  nuevo es editar una línea del YAML.
- **Reproducibilidad:** el mismo script corre idénticamente en cualquier
  máquina, eliminando el "en mi máquina funciona".

### 8.4. ¿Cómo contribuye Docker a la reproducibilidad de entornos de monitoreo?

- **Entorno idéntico en cualquier host:** la imagen `netmon-monitor` incluye
  Python 3.14, `uv` e `iputils-ping` en versiones fijas. No depende de lo que
  esté instalado en la máquina anfitriona.
- **Red virtual reproducible:** la red `netmon-net` con subred `172.28.0.0/24`
  e IPs fijas se define en `docker-compose.yml`. Levantar el entorno produce
  siempre la misma topología.
- **Simulación de condiciones adversas:** `tc netem` dentro de los contenedores
  permite introducir delay y pérdida de forma controlada y repetible, algo
  imposible de garantizar en una red física compartida.
- **Infraestructura como código:** `docker-compose.yml` versionado en git
  documenta la topología completa. Cualquier integrante del equipo reproduce
  el entorno con `make docker-up`.
- **Aislamiento:** el laboratorio no contamina ni es afectado por otras redes
  del host. Los experimentos son herméticos.

### 8.5. ¿Qué información es clave para planificar la escalabilidad de una red?

- **Baseline de rendimiento:** cuánto tráfico soporta la red actual sin
  degradación. En el laboratorio, `iperf3` midió 73.8 Gbps en loopback (no
  representativo de una red real, pero establece el techo interno).
- **Patrón de crecimiento:** a qué ritmo crece el tráfico y cuántos hosts se
  añaden por período. Sin histórico, no hay proyección posible.
- **Umbrales de degradación:** a partir de qué carga aparecen pérdida, jitter o
  aumento de RTT. En el laboratorio, 5% loss + 50 ms delay degrada seriamente
  la disponibilidad.
- **Puntos únicos de falla:** componentes sin redundancia que, al fallar,
  tumban servicios críticos. El `mtr` de Actividad 1 identificó el hop 3
  como candidato a inspección (aunque su 100% de "loss" es un artefacto de
  filtrado ICMP, no un fallo real).
- **Capacidad de absorción de ráfagas:** un enlace con throughput promedio bajo
  puede seguir sirviendo si absorbe picos. Sin medir picos, no se planifica.
- **Costo marginal de añadir capacidad:** cuánto cuesta agregar un enlace,
  un switch, o una réplica. Determina la estrategia (scale-up vs scale-out).

---

## 9. Uso del Makefile

```bash
make help              # Lista todos los targets
make setup             # Crea venv e instala dependencias con uv
make lint              # Ejecuta ruff check
make format            # ruff format + auto-fix de imports
make test              # Ejecuta pytest
make test-cov          # pytest con cobertura
make run               # Corre el script de monitoreo localmente
make docker-build      # Construye todas las imágenes
make docker-up         # Levanta la red y contenedores
make docker-down       # Baja todo
make docker-monitor    # Ejecuta el monitoreo dentro del contenedor
make docker-shell      # Shell interactivo en el contenedor monitor
make docker-targets    # Muestra reglas tc netem de los targets
make docker-clean-reports  # Corrige ownership de los reportes
make docker-clean      # Elimina contenedores, imágenes, volúmenes y redes
make clean             # Limpia caches y artefactos locales
```

---

## 10. Calidad y pruebas

- **Linter/formatter:** `ruff` con reglas `E, W, F, I, N, UP, B, C4, SIM, RUF`.
- **Tests:** `pytest` con cobertura. La suite cubre modelos, parser de config,
  motor de sondeo, generadores de reporte y orquestador CLI.
- **CI:** pipelines en GitLab (`.gitlab-ci.yml`) y GitHub Actions
  (`.github/workflows/ci.yml`) ejecutan `ruff check`, `ruff format --check` y
  `pytest` en cada push a `main` y en cada pull request.

Cobertura actual (líneas):

```
scripts/config.py            92%
scripts/models.py           100%
scripts/network_monitor.py   99%
scripts/probe.py             94%
scripts/report.py           100%
TOTAL                        97%
```

---

## 11. Autor

**Diego Alejandro Botina**
Estudiante de Ingeniería de Software - Jala University
Curso: CSNT-245 Redes de Computadoras 2

---

## 12. Licencia

MIT - ver [`LICENSE`](LICENSE).
