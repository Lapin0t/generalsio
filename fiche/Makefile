FICHES_TEX=$(wildcard langage_*.tex)

GRAPHS=$(wildcard img/graphs/*eps)

FICHES_PDF=$(FICHES_TEX:.tex=.pdf)
SOLUTIONS_PDF=$(FICHES_TEX:.tex=.correct.pdf)

# rule for files associated with a .content
#	PYTHONIOENCODIG='latin1' python parser.py $*.content | iconv -futf8 -tlatin1 > $*.inc

%.pdf: %.tex
	pdflatex -shell-escape $^

%.correct.pdf: %.tex
	pdflatex -shell-escape -jobname=$(basename $@) "\PassOptionsToClass{answers}{exam}\input{$^}"

all: $(FICHES_PDF) $(SOLUTIONS_PDF) clean

clean:
	rm -Rf *.out *.log *.aux *.toc *.bbl *.blg _minted-*



