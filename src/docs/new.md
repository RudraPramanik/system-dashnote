=Project Goal: I am building a production-ready Multi-tenant AI-native File Management System for the "DashNoteSystem."

Core Objective: To allow users to upload research papers, spreadsheets, and documents (PDF/DOCX/XLSX) that can be seamlessly synced with their existing Notes while strictly maintaining Workspace (tenant) isolation and Role-Based Access Control (RBAC).

Technical Philosophy:

Extreme Security: Never trust client-side data (MIME sniffing is mandatory).

Scalability: Storage must be decoupled (supporting Local for dev, MinIO/R2 for prod).

Modular Architecture: The Files module must be independent but able to link to Notes via a centralized association table to avoid circular dependencies.

Instruction: I will provide the implementation steps one by one. Do not look ahead and do not take shortcuts. Acknowledge this goal, then I will provide Prompt 1.
** install any package that is not already installed.
**update system.md with the new information.