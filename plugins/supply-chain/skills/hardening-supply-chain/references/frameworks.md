# Framework excerpts

Verbatim from the primary texts, read on 2026-10-29. Quote these instead of
searching. EUR-Lex answers scripted downloads with a JavaScript challenge, so
a fresh read needs a real browser (Playwright) on the HTML URL.

Sources:

- CRA: Regulation (EU) 2024/2847, <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R2847>
- AI Act: Regulation (EU) 2024/1689, <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R1689>
- NIST SP 800-218 (SSDF 1.1, final, February 2022), <https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf>.
  SSDF 1.2 (SP 800-218r1) was only an initial public draft (December 2025) when this was read.
- CIS Critical Security Controls v8.1 (August 2024), <https://researchsoc.iu.edu/resources/crosswalks/cis_controls__v8.1_guide__2024_0801.pdf>

## CRA: scope for free and open-source software

Recital 18: "the provision of products with digital elements qualifying as free
and open-source software that are not monetised by their manufacturers should
not be considered to be a commercial activity."

Recital 18: "the mere fact that an open-source software product with digital
elements receives financial support from manufacturers or that manufacturers
contribute to the development of such a product should not in itself determine
that the activity is of commercial nature. In addition, the mere presence of
regular releases should not in itself lead to the conclusion that a product
with digital elements is supplied in the course of a commercial activity."

Recital 18: "This Regulation does not apply to natural or legal persons who
contribute with source code to products with digital elements qualifying as
free and open-source software that are not under their responsibility."

Recital 19: "an intention for integration into monetised products with digital
elements includes cases where manufacturers that integrate a component into
their own products with digital elements either contribute to the development
of that component in a regular manner or provide regular financial assistance
to ensure the continuity of a software product."

Article 3(13): "'manufacturer' means a natural or legal person who develops or
manufactures products with digital elements or has products with digital
elements designed, developed or manufactured, and markets them under its name
or trademark, whether for payment, monetisation or free of charge;"

Article 3(14): "'open-source software steward' means a legal person, other than
a manufacturer, that has the purpose or objective of systematically providing
support on a sustained basis for the development of specific products with
digital elements, qualifying as free and open-source software and intended for
commercial activities, and that ensures the viability of those products;"

Article 3(22): "'making available on the market' means the supply of a product
with digital elements for distribution or use on the Union market in the course
of a commercial activity, whether in return for payment or free of charge;"

## CRA: steward obligations

Article 24(1): "Open-source software stewards shall put in place and document
in a verifiable manner a cybersecurity policy to foster the development of a
secure product with digital elements as well as an effective handling of
vulnerabilities by the developers of that product. [...] That policy shall, in
particular, include aspects related to documenting, addressing and remediating
vulnerabilities and promote the sharing of information concerning discovered
vulnerabilities within the open-source community."

Article 24(2): "Open-source software stewards shall cooperate with the market
surveillance authorities, at their request, with a view to mitigating the
cybersecurity risks posed by a product with digital elements qualifying as free
and open-source software."

Article 24(3): "The obligations laid down in Article 14(1) shall apply to
open-source software stewards to the extent that they are involved in the
development of the products with digital elements."

Article 64(10) exempts from administrative fines "any infringement of this
Regulation by open-source software stewards."

## CRA: manufacturer obligations a downstream user inherits

Article 13(8): "the support period shall be at least five years. Where the
product with digital elements is expected to be in use for less than five
years, the support period shall correspond to the expected use time."

Article 14(1): "A manufacturer shall notify any actively exploited
vulnerability contained in the product with digital elements that it becomes
aware of simultaneously to the CSIRT designated as coordinator [...] and to
ENISA."

Article 14(2): an early warning "within 24 hours", a vulnerability notification
"within 72 hours", and a final report "no later than 14 days after a corrective
or mitigating measure is available".

Annex I, Part I(2)(a): products shall "be made available on the market without
known exploitable vulnerabilities;"

Annex I, Part II. Manufacturers shall:

1. "identify and document vulnerabilities and components contained in products
   with digital elements, including by drawing up a software bill of materials
   in a commonly used and machine-readable format covering at the very least
   the top-level dependencies of the products;"
2. "address and remediate vulnerabilities without delay, including by providing
   security updates; where technically feasible, new security updates shall be
   provided separately from functionality updates;"
3. "apply effective and regular tests and reviews of the security of the
   product with digital elements;"
4. "once a security update has been made available, share and publicly disclose
   information about fixed vulnerabilities, including a description of the
   vulnerabilities, information allowing users to identify the product with
   digital elements affected, the impacts of the vulnerabilities, their
   severity and clear and accessible information helping users to remediate
   the vulnerabilities;"
5. "put in place and enforce a policy on coordinated vulnerability disclosure;"
6. "take measures to facilitate the sharing of information about potential
   vulnerabilities in their product with digital elements as well as in
   third-party components contained in that product, including by providing a
   contact address for the reporting of the vulnerabilities discovered in the
   product with digital elements;"
7. "provide for mechanisms to securely distribute updates [...] and, where
   applicable for security updates, in an automatic manner;"
8. "ensure that, where security updates are available to address identified
   security issues, they are disseminated without delay and [...] free of
   charge, accompanied by advisory messages providing users with the relevant
   information, including on potential action to be taken."

## CRA: dates

Article 71(2): "This Regulation shall apply from 11 December 2027. However,
Article 14 shall apply from 11 September 2026 and Chapter IV (Articles 35 to
51) shall apply from 11 June 2026."

## AI Act: scope

Article 3(1): "'AI system' means a machine-based system that is designed to
operate with varying levels of autonomy and that may exhibit adaptiveness after
deployment, and that, for explicit or implicit objectives, infers, from the
input it receives, how to generate outputs such as predictions, content,
recommendations, or decisions that can influence physical or virtual
environments;"

Article 2(12): "This Regulation does not apply to AI systems released under
free and open-source licences, unless they are placed on the market or put into
service as high-risk AI systems or as an AI system that falls under Article 5
or 50."

A tool that executes fixed rules and infers nothing is not an AI system. The
EU law that applies to a developer tool is the CRA.

## NIST SSDF 1.1 (SP 800-218)

- PS.1.1: "Store all forms of code – including source code, executable code,
  and configuration-as-code – based on the principle of least privilege so that
  only authorized personnel, tools, services, etc. have access."
- PS.2.1: "Make software integrity verification information available to
  software acquirers."
- PS.3.1: "Securely archive the necessary files and supporting data (e.g.,
  integrity verification information, provenance data) to be retained for each
  software release."
- PS.3.2: "Collect, safeguard, maintain, and share provenance data for all
  components of each software release (e.g., in a software bill of materials
  [SBOM])."
- PW.4.1: "Acquire and maintain well-secured software components (e.g.,
  software libraries, modules, middleware, frameworks) from commercial,
  opensource, and other third-party developers for use by the organization's
  software."
- PW.4.4: "Verify that acquired commercial, open-source, and all other
  third-party software components comply with the requirements, as defined by
  the organization, throughout their life cycles."
- RV.1.1: "Gather information from software acquirers, users, and public
  sources on potential vulnerabilities in the software and third-party
  components that the software uses, and investigate all credible reports."
- RV.1.3: "Have a policy that addresses vulnerability disclosure and
  remediation, and implement the roles, responsibilities, and processes needed
  to support that policy."
- RV.2.2: "Plan and implement risk responses for vulnerabilities."

## CIS Controls v8.1, Control 16 (IG2 and IG3)

- 16.2: "Establish and maintain a process to accept and address reports of
  software vulnerabilities, including providing a means for external entities
  to report. [...] As part of the process, use a vulnerability tracking system
  that includes severity ratings and metrics for measuring timing for
  identification, analysis, and remediation of vulnerabilities."
- 16.4: "Establish and manage an updated inventory of third-party components
  used in development, often referred to as a 'bill of materials,' as well as
  components slated for future use. This inventory is to include any risks that
  each third-party component could pose. Evaluate the list at least monthly to
  identify any changes or updates to these components, and validate that the
  component is still supported."
- 16.5: "Use up-to-date and trusted third-party software components. When
  possible, choose established and proven frameworks and libraries that provide
  adequate security. Acquire these components from trusted sources or evaluate
  the software for vulnerabilities before use."
- 16.6: "Establish and maintain a severity rating system and process for
  application vulnerabilities that facilitates prioritizing the order in which
  discovered vulnerabilities are fixed. This process includes setting a minimum
  level of security acceptability for releasing code or applications."
- 16.12: "Apply static and dynamic analysis tools within the application life
  cycle to verify that secure coding practices are being followed." (IG3 only)

## NIST CSF 2.0 (CSWP 29, February 2024)

Source: <https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf>. CSF describes outcomes
for an organisation. Its supply chain category, Govern > Cybersecurity Supply Chain Risk
Management (GV.SC): "Cyber supply chain risk management processes are identified,
established, managed, monitored, and improved by organizational stakeholders".

Subcategories a repository can show evidence for:

- GV.SC-04: "Suppliers are known and prioritized by criticality" (the inventory and SBOM).
- GV.SC-07: "The risks posed by a supplier, their products and services, and other third
  parties are understood, recorded, prioritized, assessed, responded to, and monitored over
  the course of the relationship" (advisory gate, scheduled scan, ignore entries with
  reasons).
- GV.SC-09: "Supply chain security practices are integrated into cybersecurity and
  enterprise risk management programs, and their performance is monitored throughout the
  technology product and service life cycle" (gates in CI, partly).

GV.SC-01 to -03, -05, -06, -08 and -10 concern programs, roles, contracts and supplier
relationships of the organisation. Report them as decisions for the maintainers, not as
repository gaps. SSDF is the software-producer counterpart and carries the detail.

## CIS naming

"CIS 2.0" is not a CIS document. A user who says it usually means CIS Controls
v8.1 or NIST CSF 2.0; ask which.
