#!/bin/bash

echo "=== MEDICIÓN DE TIEMPOS DE RESPUESTA ==="

# 1. Tiempo de conexión a DB
echo "📊 Base de datos:"
time psql postgresql://neondb_siacasa_owner:npg_GejQ3hYsJ9Vl@ep-bold-haze-a4cpfuu0-pooler.us-east-1.aws.neon.tech/neondb_siacasa -c "SELECT 1;" > /dev/null 2>&1

# 2. Tiempo de respuesta de OpenAI
echo "🤖 OpenAI API:"
time curl -s -X POST "https://api.openai.com/v1/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Test"}],
    "max_tokens": 10
  }' > /dev/null

# 3. Tiempo de respuesta del bot local
echo "🏠 Bot local:"
time curl -s http://localhost:3200/api/health > /dev/null 2>&1

echo "Medición completada: $(date)"
