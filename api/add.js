const { sql } = require('@vercel/postgres');

module.exports = async function handler(req, res) {
  const { a, b } = req.query;
  const result = Number(a) + Number(b);

  await sql`
    CREATE TABLE IF NOT EXISTS logs (
      id SERIAL PRIMARY KEY,
      a NUMERIC,
      b NUMERIC,
      result NUMERIC,
      created_at TIMESTAMP DEFAULT NOW()
    )
  `;
  await sql`INSERT INTO logs (a, b, result) VALUES (${a}, ${b}, ${result})`;

  res.json({ result });
};
