# 🎭 Spread - Agenda Cultural de Asturias

> **Plataforma inteligente de eventos culturales con búsqueda semántica impulsada por IA**

Spread es una API REST que agrega, indexa y permite buscar eventos culturales de toda Asturias mediante procesamiento de lenguaje natural. Utiliza embeddings vectoriales y modelos de IA para entender las consultas de los usuarios y recomendar los eventos más relevantes.

---

## ✨ Características Principales

- 🔍 **Búsqueda Semántica Inteligente**: Encuentra eventos usando lenguaje natural gracias a embeddings vectoriales (pgvector)
- 🤖 **Integración con Grok AI**: Interpreta la intención del usuario y genera respuestas conversacionales
- 🕷️ **Web Scraping Automatizado**: Recopila eventos de múltiples fuentes culturales de Asturias
- 📅 **Actualización Programada**: Cron job semanal que mantiene la base de datos actualizada
- 🎯 **Filtros Avanzados**: Por disciplina, ciudad, fecha, tipo de evento (interior/exterior, infantil, etc.)
- 🚀 **API REST con FastAPI**: Rápida, moderna y con documentación automática (OpenAPI/Swagger)

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    Cliente (Frontend)                    │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI REST API                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Endpoints  │  │  Middleware  │  │  Seguridad   │  │
│  │   /eventos   │  │     CORS     │  │  API Token   │  │
│  │ /chat-eventos│  │              │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└───────────┬─────────────────────────────────────────────┘
            │
            ├──────────────┬──────────────┬───────────────┐
            ▼              ▼              ▼               ▼
    ┌──────────────┐ ┌──────────┐ ┌─────────────┐ ┌──────────┐
    │   Scrapers   │ │  Grok AI │ │  Embeddings │ │PostgreSQL│
    │   (8 fuentes)│ │  (xAI)   │ │  (MiniLM)   │ │+pgvector │
    └──────────────┘ └──────────┘ └─────────────┘ └──────────┘
```

### Fuentes de Datos

El sistema recopila eventos de:
- 🏛️ Turismo Asturias
- 🎪 Asturies Cultura en Rede
- 🏙️ Ayuntamientos: Gijón, Oviedo, Avilés, Mieres, Siero
- 🎵 Conciertos.club
- 🎨 LABoral Ciudad de la Cultura

---

## 🚀 Instalación y Configuración

### Requisitos Previos

- Python 3.10+
- PostgreSQL con extensión pgvector
- ChromeDriver (para web scraping)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/spread.git
cd spread
```

### 2. Crear Entorno Virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Base de Datos Principal
DATABASE_URL=postgresql://usuario:password@host:puerto/database

# Base de Datos Supabase (con pgvector)
SUPABASE_DB_URL=postgresql://usuario:password@host:puerto/postgres

# Seguridad
API_SECRET_TOKEN=tu_token_secreto_aqui
MY_API_TOKEN=otro_token_si_es_necesario

# Grok AI (xAI)
GROK_API_KEY=tu_clave_de_grok_aqui

# Puerto (opcional, por defecto 8000)
PORT=8000
```

> [!IMPORTANT]
> **Nunca** subas el archivo `.env` a control de versiones. Está incluido en `.gitignore`.

### 5. Inicializar Base de Datos

```bash
# Crear tabla de eventos
python -c "from app.models import init_db; init_db()"
```

### 6. Ejecutar la Aplicación

```bash
# Desarrollo
uvicorn app.main:app --reload

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🐳 Despliegue con Docker

### Construcción de la Imagen

```bash
docker build -t spread-api .
```

### Ejecución del Contenedor

```bash
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e SUPABASE_DB_URL="postgresql://..." \
  -e API_SECRET_TOKEN="..." \
  -e GROK_API_KEY="..." \
  --name spread \
  spread-api
```

### Despliegue en Railway

El proyecto está configurado para desplegarse automáticamente en Railway:

1. Conecta tu repositorio de GitHub
2. Configura las variables de entorno en el dashboard de Railway
3. Railway detectará automáticamente el `Dockerfile` y `railway.json`

---

## 📚 Uso de la API

### Documentación Interactiva

Una vez ejecutada la aplicación, accede a:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Endpoints Principales

#### 🔓 Públicos

##### Listar Eventos
```bash
GET /eventos
GET /eventos?disciplina=concierto
GET /eventos?fecha_inicio=2024-01-01&fecha_fin=2024-12-31
```

##### Chat Inteligente con IA
```bash
GET /chat-eventos?q=conciertos de rock este fin de semana en Gijón

# Respuesta:
{
  "respuesta_llm": "Encontré 3 conciertos de rock este fin de semana...",
  "intencion": {
    "ciudad": "Gijón",
    "disciplina": "música",
    "fecha_inicio": "2024-01-20",
    "fecha_fin": "2024-01-21"
  },
  "eventos": [...]
}
```

##### Búsqueda Semántica
```bash
GET /buscar-semanticamente?q=teatro infantil navidad
```

#### 🔒 Protegidos (requieren header `X-API-Token`)

##### Ejecutar Scraping Manual
```bash
POST /scrap
Headers: X-API-Token: tu_token_secreto
```

##### Generar Embeddings
```bash
POST /generar-embeddings
Headers: X-API-Token: tu_token_secreto
```

##### Borrar Todos los Eventos
```bash
DELETE /borrar-eventos
Headers: X-API-Token: tu_token_secreto
```

---

## 🧠 Cómo Funciona la Búsqueda Inteligente

1. **Interpretación de Intención**: Grok AI analiza la pregunta del usuario y extrae:
   - Ciudad
   - Disciplina (música, teatro, cine, etc.)
   - Fechas
   - Preferencias (interior/exterior, infantil, etc.)

2. **Generación de Embedding**: La pregunta se convierte en un vector de 384 dimensiones usando `sentence-transformers/multi-qa-MiniLM-L6-cos-v1`

3. **Búsqueda Vectorial**: PostgreSQL con pgvector encuentra los eventos más similares semánticamente

4. **Filtrado Adicional**: Se aplican filtros SQL basados en la intención detectada

5. **Respuesta Natural**: Grok genera una respuesta conversacional con los eventos encontrados

---

## ⏰ Tareas Programadas

El sistema ejecuta automáticamente cada **lunes a las 3:00 AM**:
1. Borrado de eventos antiguos
2. Scraping de todas las fuentes
3. Generación de embeddings para nuevos eventos

Configuración en [main.py](app/main.py):
```python
scheduler.add_job(
    job_scrap,
    "cron",
    day_of_week="mon",
    hour=3,
    minute=0
)
```

---

## 🛠️ Tecnologías Utilizadas

| Categoría | Tecnología |
|-----------|-----------|
| **Framework** | FastAPI 🚀 |
| **Base de Datos** | PostgreSQL + pgvector |
| **ORM** | SQLAlchemy |
| **ML/IA** | sentence-transformers, Grok AI (xAI) |
| **Web Scraping** | Selenium, BeautifulSoup, Requests |
| **Parsing** | dateparser, python-dateutil |
| **Scheduler** | APScheduler |
| **Deployment** | Docker, Railway |

---

## 📁 Estructura del Proyecto

```
spread/
├── app/
│   ├── __init__.py
│   ├── main.py                 # API endpoints y configuración
│   ├── models.py               # Modelos SQLAlchemy (Railway)
│   ├── model_supabase.py       # Modelos para Supabase
│   ├── schemas.py              # Schemas Pydantic
│   ├── embeddings.py           # Generación de embeddings
│   ├── grok_intent.py          # Integración con Grok AI
│   ├── script_scraping.py      # Scrapers de todas las fuentes
│   └── save_events.py          # Lógica de guardado de eventos
├── Dockerfile                  # Configuración Docker
├── requirements.txt            # Dependencias Python
├── railway.json                # Configuración Railway
├── start.sh                    # Script de inicio
└── README.md                   # Este archivo
```

---

## 🔐 Seguridad

- ✅ Autenticación mediante API Token en headers
- ✅ Endpoints administrativos protegidos
- ✅ Variables de entorno para credenciales sensibles
- ✅ CORS configurable
- ⚠️ **Recomendación**: Implementar rate limiting en producción

---

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📝 Roadmap

- [ ] Implementar caché Redis para búsquedas frecuentes
- [ ] Añadir más fuentes de eventos
- [ ] Sistema de notificaciones por email/Telegram
- [ ] Dashboard web con React/Vue
- [ ] API de recomendaciones personalizadas
- [ ] Soporte multiidioma (asturiano, inglés)
- [ ] Tests unitarios y de integración
- [ ] Métricas y monitoring con Prometheus/Grafana

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

---

## 👤 Autor

**Álvaro Gallardo**

- GitHub: [@alvaroggallardo](https://github.com/alvaroggallardo)

---

## 🙏 Agradecimientos

- Todas las instituciones culturales de Asturias que publican sus eventos
- Comunidad de FastAPI y Python
- xAI por la API de Grok
- Proyecto pgvector por hacer posible la búsqueda vectorial en PostgreSQL

---

<div align="center">

**¿Te gusta el proyecto? ¡Dale una ⭐ en GitHub!**

Hecho con ❤️ en Asturias 🏔️

</div>