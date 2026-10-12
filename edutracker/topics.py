from dataclasses import dataclass, field

# dataclasses are like objects but less code
@dataclass
class Topic:
	key: str
	label: str
	description: str
	# field(default_factory=list) is just sating create a fresh list for each instance
	visual_cues: list[str] = field(default_factory=list)

# Make a TOPICS variable that is filled with topics
TOPICS: list[Topic] = [
	Topic(
		key="boolean_algebra",
		label="Boolean algebra",
		description=(
			"Simplification or proof of Boolean expressions using algebraic laws "
			"(De Morgan's, distribution, absorption, complement, etc.). "
			"Shown as steb-by-step equations with variables like A, B, C, etc. and operators ·, +, '."
		),
		visual_cues=[
			"Boolean equations with prime (') for complement",
			"line by line algebraic proofs with justification",
			"Symbols: A', A·B, A+B, XOR (⊕), XNOR",
		],
	),
	Topic(
		key="kmap",
		label="Karnaugh Map (K-Map)",
		description=(
			"Minimization of Boolean functions using a K-map grid. "
			"3- or 4-variable maps with 0/1 entries, Gray-code axes, "
			"and circled groupings (pairs/quads/octets) to extract SOP or POS expressions."
		),
		visual_cues=[
			"Grid/table of 0s and 1s with variable labels on axes",
			"Gray-code headers: 00, 01, 11, 10",
			"Ovals or loops circling groups of cells"
		],
	),
	Topic(
		key="nand_nor",
		label="NAND / NOR logic gate design",
		description=(
			"Logic circuit design using only NAND or only NOR gates. "
			"Derived from K-map results and redrawn with bubbled gates."
		),
		visual_cues=[
			"NAND/NOR gate symbols (D-shape with bubble)",
			"Bubble (circle) notation on gate inputs or outputs",
			"Circuit drawn beside a K-map or Boolean expression",
		],
	),
	Topic(
		key="logic_gates",
		label="Logic Gates and Truth Tables",
		description=(
			"Individual gate behavior: AND, OR, NOT, XOR, XNOR, NAND, NOR. "
			"Truth tables listing input combinations and outputs. "
		),
		visual_cues=[
			"Standard gate symbols: D-shapes, triangle with bubble (NOT)",
			"Truth table columns: A, B, Output",
			"1/0 voltage annotations",
			"Multiple gates shown individually with their tables",
		],
	),
	Topic(
		key="sequential_design",
		label="Sequential Circuit Design",
		description=(
			"Flip-flops (D, JK, SR, T), state machines, state diagrams, counters. "
			"Includes excitation tables, next-state tables, and circuit implementations."
		),
		visual_cues=[
			"State diagram: circles with arrows and transition labels",
			"Flip-flop symbols: boxes labeled D, JK, SR, or T with possible CLK input",
			"Next-state / excitation table with Q, Q+, J, K columns",
		],
	),
	Topic(
		key="number_system",
		label="Number system",
		description=(
			"Binary, hexadecimal, two's complement, IEEE. "
			"Includes step by step complement calculations and overflow detection."
		),
		visual_cues=[
			"Two's complement steps: flip bits then +1",
			"0x prefix for hex values",
			"Columns of binary addition/subtraction with carries",
			"Signed vs unsigned labels",
			"Sign, Exponent, and Mantissa for IEEE conversion"
		],
	),
	Topic(
		key="booths_algorithm",
		label="Booth algorithm",
		description=(
			"Binary multiplication using Booth's algorithim. "
			"Shows A, Q, Q-1"
		),
		visual_cues=[
			"Columns labeled A, Q, Q-1",
			"M and -M values listed",
			"Iteration count decreasing (n, n-1, ...)",
			"Final concatenated result"
		]
	),
	Topic(
		key="cpu_architecture",
		label="CPU architecture",
		description=(
			"Registers (AR, IR, PC, DR, AC), ALU, control unit, bus system, memory."
			"Instruction cycle phases: fetch (T0, T1), decode (T2), execute (T3+)."
		),
		visual_cues=[
			"Timing labels T0, T1, T2, T3",
			"Register transfer notation: AR <- IR, IR <- M[AR]",
			"Control unit with select lines S2 S1 S0",
		],
	),
	Topic(
		key="instruction_set",
		label="Instruction set",
		description=(
			"Memory-reference instructions (AND, ADD, LDA, STA, BUN, BSA, ISZ), "
			"register-reference, I/O-reference. Machine code encoding, direct/indirect addressing"
		),
		visual_cues=[
			"Instruction mnemonics: LDA, STA, BUN, BSA, ISZ",
			"16-bit binary instruction with I-bit and opcode fields",
			"Memory tables with address, label, and hex code columns",
			"Direct (I=0) vs indirect (I=1) address notation",
			"Opcode decode: D0-D7",
		],
	),
	Topic(
		key="mips",
		label="MIPS Assembly",
		description=(
			"MIPS registers ($t0, $s0, $sp), instructions (lw, sw, addi, add), "
			"stack operations, .word directive. "
		),
		visual_cues=[
			"Dollar-sign register names: $t0, $s0, $sp, $ra",
			"Instructions: lw, sw, addi, add, sub, beq, j",
			"Stack pointer operations: addi $sp, $sp, -16",
			".data / .text section labels",
		],
	),
	Topic(
		key="memory_management",
		label="Memory Management & Paging",
		description=(
			"Paging concepts: page number, page offset, page table, page size. "
			"Address spliting in 16-bit systems."
		),
		visual_cues=[
			"Address split diagram: page number | page offset bits",
			"Page table with virtual to physical mappings",
			"Page size labels: 256B, 1K, 4K",
			"Hex addresses like 0x1234 annotated with page/offset breakdown",
		],
	),
]

# Lookup by key
TOPIC_MAP = {t.key: t for t in TOPICS}