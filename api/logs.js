const { sql } = require('@vercel/postgres');

module.exports = async function handler(req, res) {
  await sql`
    CREATE TABLE IF NOT EXISTS logs (
      id SERIAL PRIMARY KEY,
      a NUMERIC,
      b NUMERIC,
      result NUMERIC,
      created_at TIMESTAMP DEFAULT NOW()
    )
  `;

  const { rows } = await sql`SELECT * FROM logs ORDER BY created_at DESC`;
  res.json(rows);
};
