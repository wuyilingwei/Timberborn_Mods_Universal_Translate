# Contributing to Timberborn Mods Universal Translate

Thank you for your interest in contributing!  
This project maintains a **large, shared translation database**.

---

## 1️⃣ Register

You need a GitHub account to contribute.

- If you don’t have one, sign up here:  
  👉 https://github.com/signup

---

## 2️⃣ Apply to Join

After creating your account, please fill out the **Join Us** form:

👉 [Join Us](https://github.com/wuyilingwei/Timberborn_Mods_Universal_Translate/issues/new?template=11-JOIN_US.yml)

Once approved, you will receive **edit permissions** for this repository.

---

## 3️⃣ Why Git (GitHub)?

Git is a tool that helps many people work on the same project **without overwriting each other’s work**.

In this project, we maintain a **large and constantly growing translation database**. Git allows us to:

- Track every change to every translation
- Know who changed what, and when
- Review and fix mistakes easily
- Restore previous versions if something goes wrong
- Let many contributors work in parallel safely

Without Git, managing hundreds of translation files from many contributors would be chaotic and error-prone.

---

## 4️⃣ Do I need to know Git?

No.

You **do not need to learn Git commands** to contribute.

You can choose **any method you feel comfortable with**:

- Edit directly in the  
  👉 [GitHub online editor](https://github.com/wuyilingwei/Timberborn_Mods_Universal_Translate/blob/main/data/)  
  *(recommended if this is your first time using Git)*
  
- Use any Git software (such as [GitHub Desktop](https://github.com/apps/desktop))  
  + clone to your local computer  
  + edit with any text editor (such as [VS Code](https://code.visualstudio.com/download) or Notepad)

More tutorial for git: [Pro Git](https://git-scm.com/book/en/v2)

We do **not** require signatures for commits.

---

## 5️⃣ Basic Files: What You Usually Edit

### Mod Translations

- Edit the appropriate **TOML files** in the `/data` directory
- These files contain the actual translation content
- See [DATA_STRUCTURE.md](DATA_STRUCTURE.md) for all format and structure details

### Global Glossary

- The global glossary is located at `data/_glossary.toml`
- It is used for **common terms shared across multiple mods**
- Please follow the rules described in [DATA_STRUCTURE.md](DATA_STRUCTURE.md)

---

## 6️⃣ Modify & Submit Changes

All changes must be submitted via **Pull Requests (PRs)**.

This ensures changes can be reviewed, tracked, and safely merged.

---

## 7️⃣ Merge Rules (Branch Protection)

To protect the `main` branch, **all changes must be merged via Pull Requests** to avoid breaking changes.

✅ You may merge by yourself if only edit `/data`

More tutorial for PR: [About pull requests](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests)

---

## 8️⃣ Advanced Files

Files outside `/data` affect project behavior, build scripts, and documentation.

If you believe such changes are necessary:

1. Open a Pull Request
2. Clearly explain the reason and impact
3. Wait for review before merging

🔒These changes **must be reviewed and approved before merging**.

> This is a **safety measure**, not a restriction.  
> It exists to protect everyone’s work and keep the project stable, and keep access tokens security.

---

## 9️⃣ Translation Rules & Limitations

This project uses **both AI and manual work**:

- AI provides fast translation support and reduces workload
- Manual work is used for proofreading and modification

We are **not responsible for the absolute accuracy** of translated text.

### Content that will NOT be translated

- **Built-in IDs**  
  These keys are used internally by the game. Modifying them may cause unpredictable behavior and violate the “universal” principle.  
  The build script will automatically detect and remove known built-in IDs.

- **Content that violates public order or morals**, including but not limited to:
  - Racial discrimination
  - Adult content
  - Hate speech

Such content will not be translated to avoid potential problems.

---

## How these change become mod?

An automatic script will:

- Generate the latest language CSV files from `/data`
- Publish updated files **every day**

# Thank you for helping make Timberborn mods accessible to more players ❤️
