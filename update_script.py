import machine
import time
import ustruct
import network
import ubinascii
from umqtt.simple import MQTTClient

# 📌 CONFIGURACIÓN
WIFI_SSID = "Troyano_2.4G"
WIFI_PASSWORD = "eros2048."

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "plc/datos"
MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id()).decode()

PLC_ID = 1  # Dirección del PLC
REGISTROS_A_LEER = [4096, 4102, 4110, 4200]  # Registros Modbus RTU a leer
INTERVALO_LECTURA = 5  # Segundos entre lecturas

# 📡 Configuración UART para Modbus RTU
uart = machine.UART(2, baudrate=9600, tx=17, rx=16, bits=8, parity=None, stop=1)
de_re = machine.Pin(4, machine.Pin.OUT)

# 📶 Conectar a Wi-Fi
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected():
        time.sleep(1)
    print("✅ Wi-Fi conectado:", wlan.ifconfig())

# 📡 Conectar a MQTT
def conectar_mqtt():
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT)
    client.connect()
    print("✅ Conectado a MQTT")
    return client

# 🔍 Cálculo de CRC-16 Modbus
def calcular_crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')

# 📡 Leer un solo registro Modbus
def leer_registro_modbus(slave_id, register_address):
    function_code = 3  # Función 03: Read Holding Register
    request = ustruct.pack('>BBHH', slave_id, function_code, register_address, 1)
    request += calcular_crc16(request)

    de_re.value(1)  # Transmisión
    uart.write(request)
    time.sleep(0.01)
    de_re.value(0)  # Recepción

    time.sleep(0.1)
    if uart.any():
        response = uart.read()
        return response
    return None

# 📊 Decodificar respuesta Modbus
def decodificar_respuesta(respuesta):
    if not respuesta or len(respuesta) < 5:
        return None
    data = respuesta[3:-2]  # Extraer datos sin CRC
    return ustruct.unpack(">H", data)[0] if len(data) == 2 else None

# 🔄 Lecturas periódicas y envío a MQTT
def ciclo_lectura_mqtt(client):
    while True:
        valores_leidos = {}
        for reg in REGISTROS_A_LEER:
            respuesta = leer_registro_modbus(PLC_ID, reg)
            valor = decodificar_respuesta(respuesta)
            if valor is not None:
                valores_leidos[reg] = valor
        
        # Convertir a JSON y enviar por MQTT
        if valores_leidos:
            mensaje = str(valores_leidos).replace("'", '"')  # Simula JSON
            client.publish(MQTT_TOPIC, mensaje)
            print("📤 Datos enviados MQTT:", mensaje)

        time.sleep(INTERVALO_LECTURA)

# 🔥 EJECUCIÓN
conectar_wifi()
mqtt_client = conectar_mqtt()
ciclo_lectura_mqtt(mqtt_client)
