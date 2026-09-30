# Actividad 1 - Monitoreo de Redes

Documento técnico que describe el diseño, la ejecución y el análisis de las
pruebas de monitoreo, diagnóstico y medición de rendimiento realizadas para el
Laboratorio de la Semana 5. Corresponde a la Actividad 1 del enunciado.

- **Materia:** CSNT-245 - Redes de Computadoras 2
- **Programa:** Ingeniería de Software - Jala University
- **Autor:** Diego Alejandro Botina
- **Sistema operativo del host administrador:** Arch Linux
- **Entorno de pruebas:** Docker Engine sobre Arch Linux

---

## 1. Objetivo

Aplicar herramientas y protocolos de red para monitorear conectividad, latencia
y rendimiento, analizando métricas reales en un entorno controlado. El entorno
se compone de dos nodos: un host administrador (Arch Linux) y un host remoto
simulado en un contenedor Docker (`netmon-iperf3`).

---

## 2. Herramientas utilizadas

| Herramienta | Propósito | Protocolo / Capa |
|---|---|---|
| `ping` | Verificación de conectividad básica | ICMP |
| `traceroute` | Análisis de rutas y latencia por salto | ICMP / TTL |
| `iperf3` | Medición de throughput TCP y UDP | TCP / UDP |
| `mtr` | Monitoreo continuo de ruta y pérdida por salto (alternativa) | ICMP |

---

## 3. Instalación de dependencias

### 3.1. En el host administrador (Arch Linux)

```bash
sudo pacman -S --needed iperf3 traceroute mtr
```

### 3.2. Verificación

```bash
iperf3 --version
traceroute --version
mtr --version
```

### 3.3. Host remoto (contenedor iperf3)

El host remoto se levanta con la imagen definida en `docker/iperf3/Dockerfile`:

```bash
make docker-build
make docker-up
```

Esto crea la red `netmon-net` (subred `172.28.0.0/24`) y el contenedor
`netmon-iperf3` con IP `172.28.0.2`, publicando los puertos 5201 TCP/UDP al
host.

Verificación de la IP del contenedor:

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' netmon-iperf3
# Esperado: 172.28.0.2
```

---

## 4. Pruebas y resultados

### 4.1. Conectividad básica con `ping`

Comando al host remoto:

```bash
ping -c 5 172.28.0.2
```

Comando a un host público (Cloudflare DNS):

```bash
ping -c 5 1.1.1.1
```

Resultados:

| Destino | Paquetes enviados | Pérdida | RTT mín | RTT prom | RTT máx | mdev |
|---|---|---|---|---|---|---|
| 172.28.0.2 (contenedor) | 5 | 0% | 0.046 ms | 0.102 ms | 0.256 ms | 0.077 ms |
| 1.1.1.1 (público) | 5 | 0% | 22.904 ms | 65.229 ms | 223.070 ms | 78.980 ms |

Observaciones:
- La latencia al contenedor es sub-milisegundo porque el tráfico atraviesa
  únicamente el puente virtual de Docker, sin salir de la máquina física.
- La latencia al destino público es coherente con la distancia geográfica,
  pero presenta una varianza alta (mdev 78.98 ms). El pico máximo de 223 ms
  indica congestión intermitente o encolamiento en algún punto del camino.
- No hay pérdida de paquetes en ninguno de los dos destinos.

Evidencia:

![Resultados de ping a destino local y público](assets/evidence/activity-1/01-ping-results.png)

### 4.2. Análisis de rutas y latencia con `traceroute`

Comando al host remoto:

```bash
traceroute -n 172.28.0.2
```

Comando al destino público:

```bash
traceroute -n 1.1.1.1
```

Resultados al host remoto (contenedor):

```
 1  172.28.0.2  0.083 ms  0.010 ms  0.007 ms
```

Resultados al destino público:

```
 1  192.168.101.1  2.309 ms  2.249 ms  2.235 ms
 2  * * *
 3  * * *
 ...
30  * * *
```

Observaciones:
- Hacia el contenedor hay un único salto: el puente virtual de Docker se
  comporta como un segmento L2, sin enrutamiento intermedio.
- Hacia el destino público solo el primer salto responde. El resto de los
  routers intermedios filtran los mensajes ICMP TTL exceeded o aplican rate
  limiting. Esto es un comportamiento esperado en redes de operadores y no
  implica una falla; simplemente no es posible obtener la ruta completa por
  ICMP sin privilegios adicionales ni sondas específicas.

Evidencia:

![Resultados de traceroute a destino local y público](assets/evidence/activity-1/02-traceroute-results.png)

### 4.3. Medición de rendimiento con `iperf3`

#### 4.3.1. Prueba TCP

```bash
iperf3 -c 172.28.0.2 -t 10
```

Resultados:

- Throughput promedio: **73.8 Gbits/sec**
- Transferencia total: 85.9 GBytes
- Retransmisiones TCP: 42 (equivalente a 0.00005% del total)
- Ventana de congestión (`Cwnd`): creció de 816 KBytes a 993 KBytes durante
  la prueba, consistente con el comportamiento de *slow start* de TCP
- Algoritmo de control de congestión reportado por el servidor: `cubic`

Evidencia:

![Resultados de iperf3 TCP](assets/evidence/activity-1/03-iperf3-tcp.png)

#### 4.3.2. Prueba UDP a 50 Mbps

```bash
iperf3 -c 172.28.0.2 -u -b 50M -t 10
```

Resultados:

- Throughput promedio: 50.0 Mbits/sec (coincide con la tasa objetivo)
- Pérdida de datagramas: 0 / 43165 (0%)
- Jitter: 0.008 ms

#### 4.3.3. Prueba UDP a 1 Gbps (saturación)

```bash
iperf3 -c 172.28.0.2 -u -b 1G -t 10
```

Resultados:

- Throughput en el receptor: 996 Mbits/sec
- Pérdida de datagramas: 3659 / 863314 (0.42%)
- Jitter: 0.002 ms

Evidencia:

![Resultados de iperf3 UDP](assets/evidence/activity-1/04-iperf3-udp.png)

Observaciones:
- En TCP, la combinación de retransmisiones y control de congestión mantiene
  la integridad de los datos a costa de pequeñas retransmisiones.
- En UDP a 50 Mbps no hay pérdida porque la tasa está muy por debajo de la
  capacidad del enlace. Al forzar 1 Gbps, aparece un 0.42% de pérdida:
  UDP no implementa control de congestión ni retransmisión, por lo que la
  pérdida es inevitable cuando la tasa de envío supera la capacidad de proceso
  o encolamiento del receptor.

### 4.4. Herramienta alternativa: `mtr`

`mtr` (My TraceRoute) combina la funcionalidad de `ping` y `traceroute` en un
único flujo continuo. A diferencia de `traceroute`, que realiza una sola
medición por salto, `mtr` mantiene estadísticas acumuladas (pérdida, RTT
promedio, mejor, peor, desviación estándar) por cada salto durante toda la
ejecución. Esto lo hace especialmente útil para detectar pérdidas
intermitentes que una captura puntual de `traceroute` no revelaría.

Comando en modo reporte al destino público:

```bash
sudo mtr -r -c 10 -n 1.1.1.1
```

Resultados:

```
HOST: zeus                      Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 192.168.101.1            0.0%    10    1.5   3.5   1.5   4.9   1.2
  2.|-- 10.100.2.1               0.0%    10    5.0   4.7   2.0   8.2   1.7
  3.|-- ???                     100.0    10    0.0   0.0   0.0   0.0   0.0
  4.|-- 192.168.70.1             0.0%    10    7.2   8.3   5.8  11.3   1.6
  5.|-- 1.1.1.1                  0.0%    10   22.1  25.5  22.1  28.0   1.9
```

Comando al host remoto:

```bash
sudo mtr -r -c 10 -n 172.28.0.2
```

Resultados:

```
HOST: zeus                      Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 172.28.0.2               0.0%    10    0.2   0.2   0.2   0.2   0.0
```

Observaciones:
- El salto 3 reporta 100% de pérdida porque ese router no responde a ICMP TTL
  exceeded de forma directa. Este es un comportamiento común y no representa
  pérdida real de tráfico, ya que los saltos posteriores (4 y 5) sí responden
  con 0% de pérdida.
- El salto final (1.1.1.1) muestra 0% de pérdida y una latencia estable de
  25.5 ms en promedio, con desviación baja (1.9 ms). Esta vista continua es
  más informativa que la de `traceroute`, que solo devolvió un salto.

Evidencia:

![Resultados de mtr a destino público](assets/evidence/activity-1/05-mtr-results.png)

---

## 5. Análisis de resultados

### 5.1. Diferencias entre TCP y UDP observadas

- **Control de congestión:** TCP ajusta dinámicamente la ventana de envío
  (`cwnd`). La prueba TCP mostró cómo la ventana creció de 816 KB a 993 KB
  durante los 10 segundos, reflejando el comportamiento de *slow start* y
  estabilización del algoritmo `cubic`. UDP no tiene este mecanismo: cuando se
  forzó la tasa a 1 Gbps, apareció pérdida del 0.42%.
- **Confiabilidad:** TCP retransmite los segmentos perdidos (42
  retransmisiones en 85.9 GBytes). UDP no retransmite; los datagramas perdidos
  son descartados por el receptor.
- **Jitter:** UDP exhibió jitter de 0.008 ms a 50 Mbps y 0.002 ms a 1 Gbps.
  TCP no reporta jitter directamente, pero el crecimiento de `cwnd` y las
  retransmisiones dan una idea de la variabilidad de la red.

### 5.2. Posibles problemas de red identificados

- **Varianza alta en el ping público:** la desviación de 78.98 ms y el pico de
  223 ms sugieren congestión intermitente o encolamiento en el camino, aunque
  no hay pérdida de paquetes.
- **Filtrado de ICMP en routers intermedios:** tanto `traceroute` como `mtr`
  muestran saltos que no responden con ICMP. No es una falla, pero limita la
  visibilidad de la ruta.
- **Pérdida UDP a saturación:** demuestra que UDP no es adecuado para
  transferencias críticas sin mecanismos de aplicación que compensen la
  pérdida.

---

## 6. Conclusiones

- La red Docker local (`172.28.0.0/24`) provee un entorno controlado con
  latencias sub-milisegundo y sin pérdida, ideal para reproducir experimentos
  de red de forma aislada y repetible.
- Las herramientas clásicas (`ping`, `traceroute`) permiten diagnosticar
  conectividad y rutas; `iperf3` cuantifica el rendimiento; `mtr` combina
  ambas aproximaciones y ofrece estadísticas acumuladas más ricas.
- Los resultados confirman la diferencia fundamental entre TCP y UDP:
  TCP prioriza la integridad mediante control de congestión y retransmisión,
  mientras que UDP prioriza la simplicidad y baja latencia, delegando la
  confiabilidad a las capas superiores.
