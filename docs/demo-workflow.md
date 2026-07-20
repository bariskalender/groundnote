# GroundNote Demo Workflow

Use an original, non-private PDF, DOCX, TXT, or Markdown document for demonstrations.

1. Check and start Foundry Local:

   ```powershell
   foundry server status
   foundry server start
   ```

2. Launch the interface:

   ```powershell
   uv run streamlit run src/groundnote/app.py
   ```

3. In the sidebar, choose one or more supported files and select **Process documents**.
4. Observe the local processing stages and confirm the document status becomes **Ready**.
5. Ask a question directly answered by the document in the main chat input.
6. Inspect the grounded answer, inline `[S1]` marker, and trusted source details.
7. Ask an unrelated question.
8. Observe the insufficient-evidence notice with no invented citation when the sources do not
   support an answer.
9. Ask `merhaba nasılsın` or `hello` and observe the immediate citation-free app response.
10. Optionally submit the same file again and observe the informational duplicate result without
   re-indexing.

GroundNote keeps chat messages in the current browser session only. Local models can make mistakes,
so important information should be verified against the cited source.
