       	Snakemake file for running RNA-Seq raw data to get the count files 

Import glob
import os
	

	#genome = ftp://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_32/GRCh38.primary_assembly.genome.fa.gz
	#gtf = ftp://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_32/gencode.v32.annotation.gtf.gz
	

	IDS,REPS = glob_wildcards("RawReads/{id}_{rep}.fastq")
	

	

	rule all:
		input:
			expand("QC/rawfastqc/{id}_{rep}_fastqc.{format}", id=IDS, rep=[1,2], format=["html","zip"]),
			expand("QC/trimming/{id}.log", id=IDS),
			expand("Trimmed/{id}_{direction}_{paired}.fastq.gz", id=IDS, direction=["forward","reverse"], paired=["paired","unpaired"]),
			expand("QC/trimmedqc/{id}_{direction}_paired_fastqc.{format}", id=IDS, direction=["forward","reverse"], format=["html","zip"]),
			expand("starOut/{id}{extension}", id=IDS, extension=["Unmapped.out.mate1","Unmapped.out.mate2","Aligned.sortedByCoord.out.bam"]),
			expand("PhiXContamination/{id}_phix.{ext}", id=IDS, ext=["sam","out"]),
			expand("KrakenOut/{id}_{ext}", id=IDS, ext=["REPORTFILE.tsv","details.out"]),
			expand("rRNAContam/{id}_{ext}", id=IDS, ext=["rrna.bam","rrna.out","rrna.sam","unmapped.bam"]),
			expand("QC/star/{id}Log.final.out", id=IDS),
			expand("QC/rRNA/{id}_rrna.out", id=IDS),
			expand("QC/microbial/{id}_REPORTFILE.tsv", id=IDS),
			expand("QC/phix/{id}_phix.out", id=IDS),
			expand("multiqc_report.{zip}", zip=["html"])
	

	rule fastqc:
		input:
			"RawReads/{id}_{rep}.fastq"
		output:
			zip="QC/rawfastqc/{id}_{rep}_fastqc.zip",
			html="QC/rawfastqc/{id}_{rep}_fastqc.html"
		params:
			path="QC/rawfastqc/"
		threads: 1
		shell:
			"~/miniconda2/bin/fastqc {input} --threads {threads} -O {params}"
	

	rule trimmomatic:
		input:
			read1="RawReads/{id}_1.fastq",
			read2="RawReads/{id}_2.fastq"
		output:
			fp="Trimmed/{id}_forward_paired.fastq.gz",
			fu="Trimmed/{id}_forward_unpaired.fastq.gz",
			rp="Trimmed/{id}_reverse_paired.fastq.gz",
			ru="Trimmed/{id}_reverse_unpaired.fastq.gz"
		log:
			"QC/trimming/{id}.log"
		threads: 4
		shell:
			"~/miniconda2/bin/trimmomatic PE -threads {threads} {input.read1} {input.read2} {output.fp} {output.fu} {output.rp} {output.ru} ILLUMINACLIP:TruSeq3-PE-2.fa:2:30:10:2:keepBothReads SLIDINGWINDOW:4:20 TRAILING:3 MINLEN:36 2>{log}"
	

	rule trimmedQC:
		input:
			"Trimmed/{id}_{direction}_paired.fastq.gz"
		output:
			zip="QC/trimmedqc/{id}_{direction}_paired_fastqc.zip",
			html="QC/trimmedqc/{id}_{direction}_paired_fastqc.html"
		params:
			path="QC/trimmedqc/"
		threads: 1
		shell:
			"~/miniconda2/bin/fastqc {input} --threads {threads} -O {params}"
	

	rule starAlignment:
		input:
			trimmed1="rRNAfreeTrimmed/{id}_forward.fastq",
			trimmed2="rRNAfreeTrimmed/{id}_reverse.fastq"
		output:
			"starOut/{id}Unmapped.out.mate1",
			"starOut/{id}Unmapped.out.mate2",
			"starOut/{id}Aligned.sortedByCoord.out.bam",
			"starOut/{id}Log.final.out"
		params:
			prefix="starOut/{id}"
		threads: 10
		shell:
			"""
			~/miniconda2/bin/STAR --runThreadN {threads} --genomeDir genomeIndex --readFilesIn {input.trimmed1} {input.trimmed2} --outFilterIntronMotifs RemoveNoncanonical --outFileNamePrefix {params.prefix} --outSAMtype BAM SortedByCoordinate  --outReadsUnmapped Fastx
			"""
	rule FeatureCounts:
		input:
			bam="starOut/{id}Aligned.sortedByCoord.out.bam"
		output:
			counts="QC/counts/readCount.{extens}"
		threads: 10
		shell:
			"~/miniconda2/bin/featureCounts -a genome/gencode.v32.annotation.gtf -o {output.counts} {input.bam} -T {threads}
	

	rule PhiXContamination:
		input:
			trimmed1="Trimmed/{id}_forward_paired.fastq.gz",
			trimmed2="Trimmed/{id}_reverse_paired.fastq.gz"
		output:
			sam="PhiXContamination/{id}_phix.sam",
			out="PhiXContamination/{id}_phix.out"
		params:
			prefix="PhiXContamination/{id}_phix",
			bowtieGenome="PhiX/Illumina/RTA/Sequence/Bowtie2Index/genome"
		threads: 10
		shell:
			"""
			~/miniconda2/bin/bowtie2 -p {threads} -x {params.bowtieGenome} -1 {input.trimmed1} -2 {input.trimmed2} -S {params.prefix}.sam &> {params.prefix}.out
			"""
	

	rule microbialContamination:
		input:
			unmapped1="starOut/{id}Unmapped.out.mate1",
			unmapped2="starOut/{id}Unmapped.out.mate2"
		output:
			report="KrakenOut/{id}_REPORTFILE.tsv",
			out="KrakenOut/{id}_details.out"
		params:
			""
		threads: 2
		shell:
			"""
			~/miniconda2/bin/krakenuniq --preload --db minikraken_20171019_8GB --threads {threads} --paired --report-file {output.report} --fastq-input {input.unmapped1} {input.unmapped2} > {output.out}
			"""
	

	rule rRNAContamination:
		input:
			trimmed1="Trimmed/{id}_forward_paired.fastq.gz",
			trimmed2="Trimmed/{id}_reverse_paired.fastq.gz"
		output:
			rnaSam="rRNAContam/{id}_rrna.sam"
		params:
			rna="RNAindex/rRNA.fa"
		threads: 10
		shell: 
			"""
			~/miniconda2/bin/bwa mem -t {threads} {params} {input.trimmed1} {input.trimmed2} > {output.rnaSam}
			"""
	

	rule rRNAContaminationConversion:
		input:
			rnaSam="rRNAContam/{id}_rrna.sam"
		output:
			rnaBam="rRNAContam/{id}_rrna.bam",
			rnaOut="rRNAContam/{id}_rrna.out",
			rnaUnm="rRNAContam/{id}_unmapped.bam"
		threads: 4
		shell:
			"""
			~/miniconda2/bin/samtools view -@ {threads} -bS -o {output.rnaBam} {input.rnaSam}
			~/miniconda2/bin/samtools flagstat -@ {threads} {output.rnaBam} > {output.rnaOut}
			~/miniconda2/bin/samtools view -@ {threads} -u -f 12 -F 256 {output.rnaBam} > {output.rnaUnm}
			"""
	

	rule rRNAfreeFastQ:
		input:
			rnaUnm="rRNAContam/{id}_unmapped.bam"
		output:
			fwd="rRNAfreeTrimmed/{id}_forward.fastq",
			rvs="rRNAfreeTrimmed/{id}_reverse.fastq"
		threads: 1
		shell:
			"""
			~/miniconda2/bin/bamToFastq -i {input} -fq {output.fwd} -fq2 {output.rvs}
			"""
	

	

	rule copyToQC:
		input:
			star="starOut/{id}Log.final.out",
			rrna="rRNAContam/{id}_rrna.out",
			micr="KrakenOut/{id}_REPORTFILE.tsv",
			phix="PhiXContamination/{id}_phix.out"
		output:
			starout="QC/star/{id}Log.final.out",
			rrnaout="QC/rRNA/{id}_rrna.out",
			microut="QC/microbial/{id}_REPORTFILE.tsv",
			phixout="QC/phix/{id}_phix.out"
		shell:
			"""
			cp {input.star} {output.starout}
			cp {input.rrna} {output.rrnaout}
			cp {input.micr} {output.microut}
			cp {input.phix} {output.phixout}
			"""
	

	rule multiqc:
		output:
			"multiqc_report.{zip}"
		shell:
			"~/miniconda2/bin/multiqc QC/."

