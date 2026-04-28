# Skills

Bu projenin ajanları için kurulu skill'ler. Her skill = bir klasör + `SKILL.md`.

## Mevcut skill'ler

```
skills/
├── plan/
│   └── SKILL.md              ← planner için
│
├── ui-ux-pro-max/
│   ├── SKILL.md              ← ui-agent için
│   └── styles.md             ← referans
│
├── api-design/
│   └── SKILL.md              ← builder (backend) için
│
├── code-review/
│   └── SKILL.md              ← reviewer için
│
└── security-review/
    └── SKILL.md              ← reviewer için
```

## Kaynaklar — Her Skill Nereden Geldi?

| Skill | Ajan | Kaynak Repo | Dosya |
|---|---|---|---|
| **plan** | planner | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | Topluluk pattern'i |
| **ui-ux-pro-max** | ui-agent | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | `.claude/skills/ui-ux-pro-max/SKILL.md` |
| **api-design** | builder | [wshobson/agents](https://github.com/wshobson/agents) | `plugins/backend-development/skills/api-design-principles/` |
| **code-review** | reviewer | [anthropics/claude-code](https://github.com/anthropics/claude-code) (resmi) | `plugins/code-review/commands/code-review.md` |
| **security-review** | reviewer | [anthropics/claude-code-security-review](https://github.com/anthropics/claude-code-security-review) (resmi) | `.claude/commands/security-review.md` |

## Ajan-skill eşleşmesi

```
planner    → plan              (planlama şablonu)
ui-agent   → ui-ux-pro-max     (frontend tasarım)
builder    → api-design        (backend API tasarımı)
reviewer   → code-review + security-review
```

## ⚠️ TDD neden skill olarak yok?

Önceki kurulumda builder'a `/tdd` skill'i vermiştim. Sonra değiştirdim çünkü:

- **Builder backend-odaklı bir ajan.** Generic TDD skill'i yerine backend-özel bir skill daha değerli.
- **TDD hâlâ builder'ın metodolojisi.** Ajan dosyasında "test-first" disiplini yazılı — skill olmasa bile uyguluyor.
- **api-design skill'i** zaten "her endpoint'e test yaz" kuralını içeriyor.

İstenirse TDD tekrar eklenebilir, ama bu projede `api-design` daha kritik.

## SKILL.md nasıl çalışıyor?

```yaml
---
name: skill-adı
description: Ne zaman tetikleneceği (bu cümle kritik — Claude buna bakıp skill'i aktif ediyor)
---
```

Sonrasında markdown formatında:
- Ne zaman aktif olur
- Yaklaşım + çıktı formatı
- Kurallar

## Kurulum kaynakları

**Resmi Anthropic:**
```bash
git clone https://github.com/anthropics/claude-code
git clone https://github.com/anthropics/claude-code-security-review
```

**Topluluk — en iyi:**
- [wshobson/agents](https://github.com/wshobson/agents) — 184 ajan + 150 skill
- [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) — 1000+ skill
- [obra/superpowers](https://github.com/obra/superpowers) — agentic framework
- [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) — 232+ skill

## Doğrulama

Claude Code'da:
```
/plan
/ui-ux-pro-max
/api-design
/code-review
/security-review
```

Veya ajan prompt'ında description tetiklendiğinde otomatik aktif.
