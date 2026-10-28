// PaperWeave graph schema. Applied by load_neo4j.py; statements are idempotent.
// Nodes:  Paper, Author            (Week 1)
//         Method, Dataset, Task    (added by entity extraction)
// Edges:  (Author)-[:WROTE]->(Paper)
//         (Paper)-[:CITES]->(Paper)
//         (Paper)-[:PROPOSES]->(Method), (Paper)-[:USES]->(Method),
//         (Paper)-[:EVALUATES_ON]->(Dataset),
//         (Paper)-[:ADDRESSES]->(Task), (Method)-[:IMPROVES_ON]->(Method)

CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.arxiv_id IS UNIQUE;
CREATE CONSTRAINT author_name IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE;
CREATE CONSTRAINT method_name IF NOT EXISTS FOR (m:Method) REQUIRE m.name IS UNIQUE;
CREATE CONSTRAINT dataset_name IF NOT EXISTS FOR (d:Dataset) REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT task_name IF NOT EXISTS FOR (t:Task) REQUIRE t.name IS UNIQUE;
CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year);
CREATE FULLTEXT INDEX paper_text IF NOT EXISTS FOR (p:Paper) ON EACH [p.title, p.abstract];
