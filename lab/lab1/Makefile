build:
	-pdflatex main.tex || true
	-bibtex main.aux || true
	-pdflatex main.tex || true
	-pdflatex main.tex || true
	-xdg-open main.pdf || true
open:
	xdg-open main.pdf