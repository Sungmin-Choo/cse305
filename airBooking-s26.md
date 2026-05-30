# Airline Reservation System
**SUNY Korea — Principles of Database Systems, Spring 2026 (Bongki Moon)**
CSE 305 Term Project

---

## Problem Statement

The goal of this project is to design and implement a relational database for an airline reservation system. You are to analyze the system requirements, design an appropriate database schema, implement the required operations using SQL, and build an application that interacts with the database. A user-interface layer (e.g., web, mobile, or command line interface) should also be implemented as a means to demonstrate database integration and its effective use in the airline reservation operations. The main focus of this project is still on database schema design, SQL query implementation, and transaction handling.

---

## Requirements & Implementation

The airline reservation system involves two roles of users. A **Staff** member registers and manages master data (e.g., airlines, airports, aircraft, seat classes), creates recurring flight schedules, generates individual flights, assigns aircraft, and views revenue statistics. A **Customer** registers an account, searches for flights by various criteria, selects seats, makes reservations with payment and ticketing, and cancels bookings with refunds.

### Schema Design

Design a database schema for your airline reservation system. You are free to design the schema however you see fit as long as it supports the key operations described below in the implementation. Your schema should include the following components.

1. **ER Diagram** — your entity-relationship diagram and design considerations such as primary key and foreign key choices, normalization analysis (e.g., 1NF, 2NF, 3NF), and integrity constraint choices (e.g., UNIQUE, CHECK, NOT NULL).
2. **Data Definition Language** — executable DDL statements (e.g., `CREATE TABLE`).

You may create sample data, and load them into the database to demonstrate that the schema works.

### Core Operations

Implement the following core operations and integrate them in your application. Each of the core operations below may require a number of dependent operations (e.g., master data management, customer registration, payment processing). Your application must support the dependent operations as well.

| Operation | Description |
|---|---|
| **Generate Flights from Schedule** | Given a recurring flight schedule (airline, route, departure/arrival times, days of week the flight operates, and the date range during which the schedule is valid), generate individual flight records for a specified date range. Each generated flight must be associated with the corresponding schedule and be ready for aircraft assignment and seat mapping. |
| **Flight Search** | Given search criteria (departure airport, arrival airport, travel date, and optionally seat class), return a list of matching flights. Each result must include: flight number, departure/arrival times, airline, and the number of remaining available seats per seat class. |
| **Create Booking** | A registered customer selects a specific seat on a specific flight and creates a booking. The system must ensure the selected seat is not already booked. Upon successful booking, payment is processed and a ticket is issued. The entire sequence (seat reservation → payment → ticketing) must be atomic — if any step fails, all changes are rolled back. |
| **Cancel Booking and Refund** | A customer can cancel an existing booking. The system must update the booking status, restore the seat to available, and process a refund. These changes must be performed atomically. The customer must be able to view their bookings before selecting one to cancel. |
| **Revenue Statistics** | Implement the following staff reports: revenue by time period (month/quarter), revenue ranked by route (departure-arrival pair), revenue breakdown by seat class as a percentage of total, and load factor (seat occupancy rate) per flight. Additional statistical queries are encouraged. |

### Advanced Features

Select either or both of the advanced features listed below, and incorporate them into your application.

1. **Indexing & Query Optimization** — Generate a large number of records to load into your database, and measure/analyze query performance on the scaled database. Use the `EXPLAIN`/`ANALYZE` feature of your DBMS query optimizer to examine execution plans with and without indexes.
2. **Triggers & Stored Procedures** — Implement some of the business logics (e.g., automatic seat availability updates) and integrity constraints (e.g., referential integrity) using triggers or stored procedures.

---

## Milestones

There are several steps you should follow to complete the project. Most of the steps will require all project groups to give a presentation in class. The members of each project group are expected to state clearly the portions of work they are responsible for and demonstrate their understandings of the work (e.g., design choices for schema and the implementation details).

1. **Project Group Formation** — All students are required to participate and complete the project in a group of three to four people. Working individually on the project is not allowed. Each group member is expected to do an equal amount of work. *(Due by: Mar/19 11:59pm)*
2. **Schema Design** — Each project group presents their schema design and the SQL statements to use for implementation. *(Presentation date: Apr/16, Slides and code due by 11:59pm)*
3. **Implementation of Core Operations** — Each project group presents how the database and the core operations are implemented, and demonstrates that their application works correctly and efficiently for the core operations. *(Presentation date: May/21, Slides and code due by 11:59pm)*
4. **Final Demonstration and Final Report** — Each project group presents how the advanced features are implemented, and demonstrates that their application works correctly and efficiently for the advanced features as well as the core operations. *(Presentation date: Jun/09, Final report due by Jun/10 11:59pm)*

---

## Final Report

Each project group must submit a final report and a code package. The final report summarizes the project by including:

1. The ER Diagram and relational schema
2. Documentation of key SQL statements and transaction logic
3. Any design alternatives that were considered (but not adopted)
4. Discussions on the challenges encountered, lessons learned, and areas for potential improvement
5. How work was divided among project group members

The code package should include a `README` file in its root folder in addition to all the code used in your application. The README file should explain how to install and run the application.

---

## Grading

| Component | Weight |
|---|---|
| Schema Design | 20% |
| Implementation of Core Operations | 30% |
| Final Demonstration and Final Report | 50% |
