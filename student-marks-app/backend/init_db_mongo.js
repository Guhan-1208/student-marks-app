/**
 * Initialization script for MongoDB
 * Creates:
 *  - Unique indexes
 *  - Default admin user
 *
 * Run inside the backend container or from host using:
 *   docker-compose exec mongo mongosh /app/init_db_mongo.js
 */

const bcrypt = require("bcrypt");
const { MongoClient } = require("mongodb");

const MONGO_URI = process.env.MONGO_URI || "mongodb://mongo:27017/student_marks_db";
const DB_NAME = "student_marks_db";

// Admin credentials (you can change these)
const ADMIN_EMAIL = "admin@example.com";
const ADMIN_PASSWORD = "admin123"; // CHANGE THIS IN PRODUCTION

async function run() {
  console.log("Connecting to MongoDB:", MONGO_URI);
  const client = new MongoClient(MONGO_URI);

  await client.connect();
  const db = client.db(DB_NAME);

  const students = db.collection("students");
  const staff = db.collection("staff");
  const marks = db.collection("marks");

  console.log("Creating indexes...");

  await students.createIndex({ register_number: 1 }, { unique: true });
  await staff.createIndex({ email: 1 }, { unique: true });
  await marks.createIndex({ register_number: 1 });

  console.log("Indexes created.");

  console.log("Checking admin user...");

  let existingAdmin = await staff.findOne({ email: ADMIN_EMAIL });

  if (!existingAdmin) {
    const hashed = await bcrypt.hash(ADMIN_PASSWORD, 10);

    await staff.insertOne({
      email: ADMIN_EMAIL,
      password_hash: hashed,
      role: "admin",
      created_at: new Date()
    });

    console.log("Admin user created:");
    console.log(" Email:", ADMIN_EMAIL);
    console.log(" Password:", ADMIN_PASSWORD);
  } else {
    console.log("Admin user already exists.");
  }

  await client.close();
  console.log("MongoDB initialization complete.");
}

run().catch((err) => console.error(err));
