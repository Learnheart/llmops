"""
Compliance Guardrail Strategy.
Ensures adherence to regulatory and legal requirements.
"""

from app.templates.base import GuardrailStrategy


class ComplianceStrategy(GuardrailStrategy):
    """
    Guardrail to ensure regulatory and legal compliance.
    """

    name = "compliance"
    description = "Ensures adherence to regulatory and legal requirements (GDPR, HIPAA, etc.)"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build compliance guardrail.

        Args:
            user_context: Description of regulatory context
            **kwargs: Additional parameters (regulations, jurisdiction)
        """
        regulations = kwargs.get("regulations", ["GDPR"])
        jurisdiction = kwargs.get("jurisdiction", "EU")
        industry = kwargs.get("industry", "general")

        regulations_list = ", ".join(regulations)

        return f"""# Compliance Guardrail

## Context
{user_context}

## Applicable Regulations: {regulations_list}
## Jurisdiction: {jurisdiction}
## Industry: {industry.title()}

## Regulatory Compliance Requirements

{self._get_regulation_requirements(regulations)}

## General Compliance Principles

### Data Handling
1. **Data Minimization**: Only collect and process necessary data
2. **Purpose Limitation**: Use data only for stated purposes
3. **Storage Limitation**: Don't retain data longer than necessary
4. **Accuracy**: Ensure data is accurate and up-to-date
5. **Security**: Implement appropriate security measures

### User Rights
1. **Right to Information**: Clear communication about data use
2. **Right to Access**: Users can request their data
3. **Right to Rectification**: Users can correct their data
4. **Right to Erasure**: Users can request data deletion
5. **Right to Portability**: Users can transfer their data
6. **Right to Object**: Users can object to processing

### Consent Management
- Obtain explicit consent before data processing
- Make consent withdrawal as easy as giving it
- Keep records of consent
- Don't use pre-ticked boxes
- Separate consent for different purposes

### Required Disclosures
Always inform users about:
- What data is collected
- Why it's collected
- How it's used
- Who has access to it
- How long it's retained
- Their rights regarding the data

## Industry-Specific Requirements

{self._get_industry_requirements(industry)}

## Prohibited Activities

### Never Do:
- Process data without legal basis
- Share data with unauthorized parties
- Retain data beyond necessary period
- Use data for undisclosed purposes
- Make automated decisions without human review (when required)
- Transfer data outside approved jurisdictions without safeguards
- Ignore data subject requests
- Fail to report breaches within required timeframe

### Always Do:
- Document legal basis for processing
- Implement privacy by design
- Conduct data protection impact assessments (when required)
- Maintain processing records
- Have data breach response procedures
- Honor user rights requests promptly
- Provide clear privacy notices
- Implement appropriate security measures

## Response Guidelines

### When Handling Personal Data:
1. Verify legal basis exists
2. Apply data minimization
3. Ensure security measures
4. Document the processing
5. Respect user rights

### When Responding to Users:
1. Provide clear, plain language explanations
2. Include required disclosures
3. Explain their rights
4. Offer opt-out mechanisms
5. Provide contact information for questions

### Red Flags - Stop Immediately:
- Request to process sensitive data without clear authorization
- Instruction to bypass consent requirements
- Request to share data with unauthorized parties
- Instruction to retain data indefinitely
- Request to make high-impact automated decisions without review
- Attempt to transfer data to non-compliant jurisdiction

## Breach Response Protocol

If a potential data breach is detected:
1. Immediately stop the activity
2. Escalate to appropriate personnel
3. Document the incident
4. Follow breach notification procedures
5. Implement remediation measures

## Disclaimer Requirements

Include appropriate disclaimers:
- "This is not legal advice. Consult with qualified professionals."
- "Compliance requirements vary by jurisdiction."
- "This information is current as of [date]."
- "Individual circumstances may require additional measures."

## Audit Trail

Maintain records of:
- What data was processed
- When it was processed
- Why it was processed
- Who authorized the processing
- What security measures were applied
"""

    def _get_regulation_requirements(self, regulations: list) -> str:
        """Get specific requirements for each regulation."""
        requirements = {
            "GDPR": """### GDPR (General Data Protection Regulation)
- **Scope**: EU residents' personal data
- **Key Requirements**:
  - Lawful basis for processing (consent, contract, legal obligation, etc.)
  - Data protection principles (lawfulness, fairness, transparency)
  - User rights (access, rectification, erasure, portability, objection)
  - Data breach notification (72 hours to supervisory authority)
  - Privacy by design and default
  - Data Protection Impact Assessments for high-risk processing
  - DPO appointment (when required)
- **Penalties**: Up to €20M or 4% of global turnover""",
            "HIPAA": """### HIPAA (Health Insurance Portability and Accountability Act)
- **Scope**: Protected Health Information (PHI) in the US
- **Key Requirements**:
  - Privacy Rule: Limits on PHI use and disclosure
  - Security Rule: Administrative, physical, technical safeguards
  - Breach Notification Rule: Notify affected individuals and HHS
  - Minimum necessary standard: Only access/use PHI needed
  - Business Associate Agreements required
  - Patient rights: Access, amendment, accounting of disclosures
- **Penalties**: Up to $1.5M per violation category per year""",
            "CCPA": """### CCPA (California Consumer Privacy Act)
- **Scope**: California residents' personal information
- **Key Requirements**:
  - Consumer rights: Know, delete, opt-out, non-discrimination
  - Notice at collection required
  - Privacy policy disclosure requirements
  - Opt-out of sale of personal information
  - Opt-in for minors under 16
  - Reasonable security measures
  - 30-day cure period for violations
- **Penalties**: Up to $7,500 per intentional violation""",
            "PCI-DSS": """### PCI-DSS (Payment Card Industry Data Security Standard)
- **Scope**: Payment card data
- **Key Requirements**:
  - Build and maintain secure network
  - Protect cardholder data (encryption)
  - Maintain vulnerability management program
  - Implement strong access control measures
  - Regularly monitor and test networks
  - Maintain information security policy
  - Never store sensitive authentication data after authorization
- **Penalties**: Fines from payment brands, potential card processing restrictions""",
            "SOC2": """### SOC 2 (Service Organization Control 2)
- **Scope**: Service providers handling customer data
- **Key Requirements**:
  - Security: Protection against unauthorized access
  - Availability: System available for operation and use
  - Processing Integrity: System processing is complete, valid, accurate, timely
  - Confidentiality: Confidential information protected
  - Privacy: Personal information collected, used, retained, disclosed per commitments
- **Validation**: Independent auditor assessment""",
        }

        result = []
        for reg in regulations:
            if reg in requirements:
                result.append(requirements[reg])
            else:
                result.append(f"### {reg}\n- Refer to specific {reg} documentation for requirements")

        return "\n\n".join(result)

    def _get_industry_requirements(self, industry: str) -> str:
        """Get industry-specific compliance requirements."""
        requirements = {
            "healthcare": """### Healthcare Industry
- Comply with HIPAA for PHI
- Implement minimum necessary access
- Maintain audit logs for PHI access
- Encrypt PHI in transit and at rest
- Business Associate Agreements required
- Patient consent for specific uses
- Breach notification within 60 days""",
            "finance": """### Financial Services
- Comply with GLBA, PCI-DSS, SOX (as applicable)
- Implement strong authentication
- Encrypt financial data
- Maintain transaction audit trails
- Privacy notices required
- Opt-out rights for information sharing
- Incident response and reporting procedures""",
            "education": """### Education Sector
- Comply with FERPA for student records
- Parental consent for children under 13 (COPPA)
- Limit access to educational records
- Allow parents to review and correct records
- Obtain consent before disclosure
- Maintain security of educational records""",
            "retail": """### Retail Industry
- Comply with PCI-DSS for payment data
- CCPA/GDPR for customer data (jurisdiction-dependent)
- Clear privacy policies
- Secure customer data
- Opt-out mechanisms for marketing
- Data breach notification procedures""",
            "general": """### General Industry
- Follow applicable data protection laws (GDPR, CCPA, etc.)
- Implement reasonable security measures
- Provide privacy notices
- Honor user rights requests
- Report breaches as required
- Maintain compliance documentation""",
        }
        return requirements.get(industry.lower(), requirements["general"])

    def get_parameters(self):
        return {
            "regulations": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["GDPR", "HIPAA", "CCPA", "PCI-DSS", "SOC2", "FERPA", "COPPA"],
                },
                "default": ["GDPR"],
                "description": "Applicable regulations",
            },
            "jurisdiction": {
                "type": "string",
                "default": "EU",
                "description": "Legal jurisdiction (e.g., EU, US, UK)",
            },
            "industry": {
                "type": "string",
                "enum": ["general", "healthcare", "finance", "education", "retail"],
                "default": "general",
                "description": "Industry sector",
            },
        }
