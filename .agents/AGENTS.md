# Core Operational Rules

1. **Never Remove Data:** Do not delete or remove anyone currently in the database. When adding new people or features, merge them and tag them (e.g., "newly added" or "new feature").
2. **Improve & Align:** Old or existing data/code should only be improved, corrected, fixed, and aligned correctly. 
3. **Local-Only Enforced:** Until explicit permission is given by the user, **everything must be done locally**. Absolutely no code will be pushed to production branches (like `main`) or deployed to live servers (Render/Vercel) without direct authorization.
4. **Maximum Cost/Credit Optimization:** The maximum API credits, bandwidth, and compute resources that can be saved, MUST be saved. Always opt for the most limit-friendly, budget-conscious architecture.
5. **Strict Verification & Push Protocol:** Never push anything to production until the user explicitly says so at least 2 times. Apply the strict implementation and verification protocol to every task: Never mark a task as complete based only on code being added; observe real-world outcomes, cross-check through DB/API/UI, and test edge cases.
6. **Local Verification Loops:** After finishing every task, update, or improvement, verify the change on the local environment at least 4 times with a gap of 1 minute between each check. Provide a screenshot of the local frontend after every check to prove it works. Only after the 4th successful check can you provide the final confirmation to the user.
