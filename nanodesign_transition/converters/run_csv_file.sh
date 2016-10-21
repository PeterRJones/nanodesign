#-------------------------------------------------------------------------------------#
#                     run the converter with a sequence file name.                    #
#-------------------------------------------------------------------------------------#
# Set the cadnano design files directory.
data=../../tests/samples

fn=fourhelix
seq=M13mp18
outfile=./results/${fn}_viewer.json 

converter.py --infile=${data}/${fn}.json             \
             --inseqfile=${data}/${fn}_${seq}.csv    \
             --informat="cadnano"                    \
             --outfile=${outfile}                    \
             --outformat="viewer"

