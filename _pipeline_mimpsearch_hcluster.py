import os, datetime, sys, subprocess
starttime_unformatted = datetime.datetime.now()
starttime = datetime.datetime.now().strftime("%y.%m.%d_%Hh%Mm%S")
from optparse import OptionParser
#######################################################################
####[EDIT THESE VARIABLES TO SET STUFF BEFORE RUNNING THE PIPELINE]####
#######################################################################

# Dependencies:
# - SignalP
# - AUGUSTUS
# - BioPython 
# - python package "BCBio"
# - R libraries "gplots" and "ctc" must be installed!

blastdatabasedir			= '/Users/Peter/Documents/Sequences/Fo_genomes/blastdbs'
contigprefix 				= 'contig_' #contig_
AUGUSTUS_path 				= '/Users/Peter/Programming/augustus-3.1/bin/augustus'
AUGUSTUS_CONFIG_path 		= '/Users/Peter/Programming/augustus-3.1/config'
BLASTbindir 				= '/usr/local/ncbi/blast/bin'
SignalPpath					= '/Users/Peter/Programming/signalp/signalp-4.1/signalp'


#mimp-search variables
distance_MetStop			= '2500' 		# sequence downstream of motif used for ORF prediction
distance_Augustus			= '5000' 		# sequence downstream of motif used for ORF prediction
min_prot_len				= '25'   		# in aa
max_prot_len				= '600'  		# in aa
max_d2m						= '2000' 		# max distance between mimp TIR and start-codon
SignalP_threshold			= '0.550'

#blast variables
PERC_IDENTITY_THRESH 		= '30'
BLAST_task					= 'blastn' #or megablast
buildblastdb				= 'no'
#clustering variables:
distance_matrix_rows		= '1'
clustering_method_rows		= 'average'
distance_matrix_cols		= '1'
clustering_method_cols		= 'average'

#1 = Jaccard index (1901) S3 coefficient of Gower & Legendre s1 = a / (a+b+c)
#2 = Simple matching coefficient of Sokal & Michener (1958) S4 coefficient of Gower & Legendre s2 = (a+d) / (a+b+c+d)
#3 = Sokal & Sneath(1963) S5 coefficient of Gower & Legendre s3 = a / (a + 2(b + c))
#4 = Rogers & Tanimoto (1960) S6 coefficient of Gower & Legendre s4 = (a + d) / (a + 2(b + c) +d)
#5 = Dice (1945) or Sorensen (1948) S7 coefficient of Gower & Legendre s5 = 2a / (2a + b + c)
#6 = Hamann coefficient S9 index of Gower & Legendre (1986) s6 = (a - (b + c) + d) / (a + b + c + d)
#7 = Ochiai (1957) S12 coefficient of Gower & Legendre s7 = a / sqrt((a + b)(a + c))
#8 = Sokal & Sneath (1963) S13 coefficient of Gower & Legendre s8 = ad / sqrt((a + b)(a + c)(d + b)(d + c))
#9 = Phi of Pearson S14 coefficient of Gower & Legendre s9 = (ad - bc) / sqrt((a + b)(a + c)(d + b)(d + c))
#10 = S2 coefficient of Gower & Legendre S10 = a / (a + b + c + d)

UseNonRedundantEffectors	= False 		#(step C)
#######################################################################


currentdir = os.path.dirname(os.path.realpath(__file__))
scriptdir = currentdir.split('/')[-1]
default_outputdir = currentdir.split(scriptdir)[0]+'output_'+starttime



usage = 'python _pipeline_mimpsearch_hcluster.py -i [infile] <options>\n'+'-'*20+'\n\
This script will take a folder with genome fasta files, find mimps and mimp terminal inverted repeats and try to identify candidate effectors. These will be clustered into families and then \
BLASTed against each of the genomes to identify presence or absence. These binary patterns will be clustered to produce a clustering figure. \n-Peter van Dam (feb 2016)'
parser = OptionParser(usage=usage)

parser.add_option("-i", "--in", dest="infolder", help="provide a folder with genome fasta files")
parser.add_option("-o", "--out", dest="outfolder", help="output folder; default is: ../output_+starttime")
parser.add_option("-e", "--effector_fasta", dest="effector_fasta", help="Skip the effector prediction pipeline and go straight go to blasting and clustering using a self-supplied effector list in fasta format.")
parser.add_option("-m", "--metstoppredictiononly", dest="MetStopPredictionOnly", action="store_true", default=False,
					help="Do not use Augustus gene prediction, only first met to first stop.")

(options, args) = parser.parse_args()

if options.infolder == None:
	print '\n[ERROR!]\nPlease specify a folder containing Fusarium oxysporum genomes.\n'
	print '"-i infolder"'
	print 'Use "-h" to see additional options.\n'
	quit()
else: 
	genomedir = options.infolder
	if " " in genomedir:
		print '\n[ERROR!]\nThis input folder contains a space, which may lead to problems: '+genomedir+'\nExiting..'
	if not os.path.exists(genomedir):
		print '\n[ERROR!]\nThis input folder could not be found: '+genomedir+'\nExiting..'
		quit()
	genomefoldername = os.path.basename(os.path.normpath(genomedir))

if options.outfolder == None:
	outputdir = default_outputdir
else:
	outputdir = options.outfolder

if options.effector_fasta == None:
	####[A. Identify mimp-terminal inverted repeats and find ORFs with a Signal Peptide within a downstream region]####
	cline1a = ' '.join(['python', currentdir+'/01a.mimpfinder_combine_to_putefflist_MetStop.py', genomedir, outputdir, contigprefix, distance_MetStop, min_prot_len, max_prot_len, max_d2m, SignalPpath, SignalP_threshold])
	print cline1a, os.system(cline1a)

	if options.MetStopPredictionOnly:
		print 'No Augustus gene prediction will be executed.'
	else:
		cline1b = ' '.join(['python', currentdir+'/01b.mimpfinder_combine_to_putefflist_AUGUSTUS.py', genomedir, outputdir, contigprefix, AUGUSTUS_path, '--AUGUSTUS_CONFIG_PATH='+AUGUSTUS_CONFIG_path, distance_Augustus, min_prot_len, max_prot_len, max_d2m, SignalPpath, SignalP_threshold])
		print cline1b, os.system(cline1b)


	####[B. Reduce redundancy in each putative effector output file:]####
	all_putative_effectors_MetStop = outputdir+'/01.mimpfinder/'+genomefoldername+'_MetStopOut/all_putative_effectors.fasta'
	all_putative_effectors_Augustus = outputdir+'/01.mimpfinder/'+genomefoldername+'_AugustusOut/all_putative_effectors.fasta'
	leave_put_eff_identifiers_during_clustering = 'TRUE'

	cline2a = ' '.join(['python', currentdir+'/02.cluster_putefflists.py', all_putative_effectors_MetStop, blastdatabasedir, leave_put_eff_identifiers_during_clustering, BLASTbindir])
	print cline2a, os.system(cline2a)
	if options.MetStopPredictionOnly:
		print 'No clustering of Augustus effectors necessary.'
	else:
		cline2b = ' '.join(['python', currentdir+'/02.cluster_putefflists.py', all_putative_effectors_Augustus, blastdatabasedir, leave_put_eff_identifiers_during_clustering, BLASTbindir])
		print cline2b, os.system(cline2b)
	# now, the outputs of both metstop and augustus are clustered.

	####[C. Concatenate and cluster output from MetStop and Augustus (either using raw output or clustered output):]####
	all_putative_effectors_MetStop_clustered = all_putative_effectors_MetStop.split('.fa')[0]+'_clustered.fasta'
	all_putative_effectors_Augustus_clustered =  all_putative_effectors_Augustus.split('.fa')[0]+'_clustered.fasta'
	if not os.path.exists(outputdir+'/02.cluster_putative_effectors/'):
		os.makedirs(outputdir+'/02.cluster_putative_effectors/')
	all_putative_effectors_concatenated = outputdir+'/02.cluster_putative_effectors/all_putative_effectors_concatenated.fasta'

	if options.MetStopPredictionOnly:
		if UseNonRedundantEffectors == False:
			clinecat = 'cat '+all_putative_effectors_MetStop+' > '+all_putative_effectors_concatenated
		else:
			clinecat = 'cat '+all_putative_effectors_MetStop_clustered+' > '+all_putative_effectors_concatenated
	else:
		if UseNonRedundantEffectors == False:
			clinecat = 'cat '+all_putative_effectors_MetStop+' '+all_putative_effectors_Augustus+' > '+all_putative_effectors_concatenated
		else:
			clinecat = 'cat '+all_putative_effectors_MetStop_clustered+' '+all_putative_effectors_Augustus_clustered+' > '+all_putative_effectors_concatenated
	print clinecat, os.system(clinecat)

	####[D. Cluster fasta file containing all concatenated effectors identified so that each effector occurs once in the list:]####
	leave_put_eff_identifiers_during_clustering = 'FALSE'
	cline2c = ' '.join(['python', currentdir+'/02.cluster_putefflists.py', all_putative_effectors_concatenated, blastdatabasedir, leave_put_eff_identifiers_during_clustering, BLASTbindir])
	print cline2c, os.system(cline2c)
	all_putative_effectors_concatenated_clustered = all_putative_effectors_concatenated.split('.fa')[0]+'_clustered.fasta'

else: #an own list of putative effectors was supplied to be blasted and clustered:
	if options.effector_fasta.endswith('.fa') or options.effector_fasta.endswith('.fasta') or options.effector_fasta.endswith('.fas'):
		all_putative_effectors_concatenated_clustered = options.effector_fasta

####[E. BLASTN for presence/absence scoring:]####
cline3 = ' '.join(['python', currentdir+'/03.local_blast_clustered_putefflist_to_pres-abs_table.py', all_putative_effectors_concatenated_clustered, genomedir, blastdatabasedir, BLASTbindir, outputdir, PERC_IDENTITY_THRESH, BLAST_task, buildblastdb])
print cline3, os.system(cline3)
cline3_output = outputdir+'/03.blastn_presence_absence/blastn_presence_absence.txt'


####[F. Use R script for hierarchical clustering:]####
cline4_outputdir = outputdir+'/04.cluster_and_plot/'
if not os.path.exists(cline4_outputdir):
	os.makedirs(cline4_outputdir)
cline4 = ' '.join(['Rscript', currentdir+'/04.cluster_and_plot_heatmap3.R', currentdir+'/heatmap.3.R', cline3_output, cline4_outputdir, distance_matrix_rows, clustering_method_rows, distance_matrix_cols, clustering_method_cols])
print cline4, os.system(cline4)


log_txt = open(outputdir+"/log_txt.txt", "w")
if options.effector_fasta != None:
	write_this = ' '.join(["distance_MetStop, distance_Augustus, min_prot_len, max_prot_len, max_d2m, SignalP_threshold, commands\n\n", distance_MetStop, distance_Augustus, min_prot_len, max_prot_len, max_d2m, SignalP_threshold, '\n\n', cline3, '\n\n', cline4])
else:
	write_this = ' '.join(["distance_MetStop, distance_Augustus, min_prot_len, max_prot_len, max_d2m, SignalP_threshold, commands\n\n", distance_MetStop, distance_Augustus, min_prot_len, max_prot_len, max_d2m, SignalP_threshold, '\n\n', cline1a, '\n\n', cline1b, '\n\n', cline2a, '\n\n', cline2b, '\n\n', clinecat, '\n\n', cline2c, '\n\n', cline3, '\n\n', cline4])
log_txt.write(write_this)
log_txt.close()


print '-----------------------'
print '\n\nStarttime:', starttime
print 'Endtime', datetime.datetime.now().strftime("%y.%m.%d_%Hh%Mm%S")
print '-----------------------'
print 'Total time used for whole script:', (datetime.datetime.now()-starttime_unformatted)
print '-----------------------'