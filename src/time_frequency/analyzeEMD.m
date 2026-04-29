function analyzeEMD(dataFile,fontName)
    arguments
            dataFile
            fontName = 'TeX Gyre Heros';
    end

    clc; close all;
    includePackage('math','graphics');

    [filepath,name] = fileparts(dataFile);
    savepath = fullfile(filepath,name);
    if ~isfolder(savepath)
        mkdir(savepath);
    end

    % --- Signal ---
    S = load(dataFile);

    t = double(S.t);
    x = S.x;
    L = double(S.L);
    Ts = double(S.Ts);

    tDate  = datetime(1970,1,1) + days(t);
    tYears = year(tDate) + (day(tDate,'dayofyear') - 1) ./ 365;
    
    pm = PlotManager();
    pm.createFigure('size',[2,1],'font',fontName);
    pm.plot(tYears,x);
    pm.xlim([min(tYears),max(tYears)]);
    pm.xlabel('t (years)');
    pm.ylabel('x(t)');
    pm.format();
    pm.save(fullfile(savepath,'emd_signal.png'));
    
    % --- Analysis ---
    noiseStd  = 0.2 * std(x);
    numEnsembles = 200;
    
    seed = 13;
    rng(seed);

    % First pass to determine number of IMFs
    imf0 = emd(x);
    N = size(imf0,2);

    % Ensemble accumulator
    imfSum = zeros(L,N);
    for ii = 1:numEnsembles
        w = noiseStd * randn(size(x));
        z = x + w;

        imf = emd(z);
        n = size(imf,2);

        % Align number of IMFs — pad or truncate to match nIMF
        if n < N
            imf = [imf,zeros(L,N - n)]; %#ok<AGROW>
        elseif n > N
            % Merge excess IMFs into last column
            imf(:,N) = sum(imf(:,N:end),2);
            imf = imf(:,1:N);
        end

        imfSum = imfSum + imf;
    end
    imfs = imfSum / numEnsembles;

    % Residual
    residual = x - sum(imfs,2)';
    
    pm = PlotManager();
    pm.createFigure('size',[N + 1,1],'font',fontName);
    for ii = 1:N
        pm.selectAxis(ii);
        pm.plot(tYears,imfs(:,ii),'k');
        pm.ylabel(sprintf('IMF_{%d}',ii-1));
        pm.xlim([tYears(1),tYears(end)]);
    end
    pm.selectAxis(N + 1);
    pm.plot(tYears,residual,'k');
    pm.ylabel('Residual');
    pm.xlim([tYears(1),tYears(end)]);
    pm.xlabel('t (years)');
    pm.save(fullfile(savepath,'emd_imfs.png'));
    
    % Energy
    E = sum(imfs.^2,1);

    pm = PlotManager();
    pm.createFigure('font',fontName);
    pm.plot(0:N - 1,db(E + eps),'o-');
    pm.xticks(0:N - 1);
    pm.xticklabels(arrayfun(@(k) sprintf('IMF_{%d}',k),0:N - 1,'UniformOutput',false));
    pm.ylabel('Energy (dB)');
    pm.title('EEMD Energy Spectrum');
    pm.format();
    pm.save(fullfile(savepath,'emd_energy.png'));
    
    % Instantaneous features
    instAmp = zeros(L,N);
    instFreq = zeros(L,N);
    instPhase = zeros(L,N);

    for ii = 1:N
        hht = hilbert(imfs(:,ii));

        instAmp(:,ii) = abs(hht);
        instPhase(:,ii) = unwrap(angle(hht));
        phaseDiff = diff(instPhase(:,ii));
        instFreq(:,ii) = [phaseDiff(1); phaseDiff] / (2 * pi * Ts);
    end
    
    meanPeriod = zeros(1,N);
    for ii = 1:N
        validFreq = instFreq(:,ii);
        validFreq = clip(validFreq,0,inf);
        if ~isempty(validFreq)
            meanPeriod(ii) = 1 / mean(validFreq);
        end
    end

    pm = PlotManager();
    pm.createFigure('size',[N,1],'font',fontName);
    for ii = 1:N
        pm.selectAxis(ii);
        pm.plot(tYears,instAmp(:,ii),'k');
        pm.xlim([tYears(1),tYears(end)]);
        pm.ylabel(sprintf('IMF_{%d}',ii - 1));
    end
    pm.xlabel('t (years)');
    pm.sgtitle('IMF Amplitudes');
    pm.save(fullfile(savepath,'emd_imf_amplitudes.png'));

    pm = PlotManager();
    pm.createFigure('size',[N,1],'font',fontName);
    for ii = 1:N
        pm.selectAxis(ii);
        instFreqSmoothed = medfilt1(instFreq(:,ii),11);
        instFreqSmoothed(instFreqSmoothed <= 0) = nan;
        isntPeriodSmooth = 1 ./ instFreqSmoothed;
        pm.plot(tYears,isntPeriodSmooth,'k');
        pm.xlim([tYears(1),tYears(end)]);
        pm.ylabel(sprintf('IMF_{%d}',ii - 1));
    end
    pm.xlabel('t (years)');
    pm.sgtitle('IMF Periods');
    pm.save(fullfile(savepath,'emd_imf_periods.png'));

    % Hilbert spectrum  
    pm = PlotManager();
    pm.createFigure('hold','on','font',fontName);
    for ii = 1:N
        instFreqK = instFreq(:,ii);
        instAmpK  = instAmp(:,ii);

        I = instFreqK > 0 & instFreqK < 1;
        instPeriodK  = zeros(L,1);
        instPeriodK(I) = 1 ./ instFreqK(I);
        instPeriodK(~I) = nan;
        pm.scatter(tYears(I),log2(instPeriodK(I)),20,instAmpK(I),'s','filled');
    end
    periodTicks = 2.^(log2(1):round(log2(max(instPeriodK))));
    pm.yticks(log2(periodTicks));
    pm.yticklabels(arrayfun(@(p) sprintf('%d',round(p)),periodTicks,'UniformOutput',false));
    pm.xlim([tYears(1),tYears(end)]);
    pm.colorbar('Label','Magnitude');
    pm.colormap(plasma(256));
    pm.xlabel('t (years)');
    pm.ylabel('Period (days)');
    pm.title('Hilbert Spectrum (HHT)');
    pm.format();
    pm.save(fullfile(savepath,'emd_hilbert_spectrum.png'));

    % Decompose components into scales
    annualMask = meanPeriod >= 180 & meanPeriod <= 540;
    trendMask = meanPeriod > 540;
    noiseMask = meanPeriod < 180;

    annualComponent = sum(imfs(:,annualMask),2)';
    trendComponent = sum(imfs(:,trendMask),2)' + residual;
    noiseComponent = sum(imfs(:,noiseMask),2)';

    pm = PlotManager();
    pm.createFigure('size',[3,1],'hold','on','font',fontName);
    pm.selectAxis(1);
    pm.plot(tYears,trendComponent);
    pm.plot(tYears,x);
    pm.xlim([tYears(1),tYears(end)]);
    pm.legend({'Trend','Original'},'Location','eastoutside');
    pm.ylabel('EVI');
    pm.title('Inter-annual Trend Component');
    pm.selectAxis(2);
    pm.plot(tYears,annualComponent);
    pm.plot(tYears,x);
    pm.xlim([tYears(1),tYears(end)]);
    pm.legend({'Annual','Original'},'Location','eastoutside');
    pm.ylabel('EVI');
    pm.title('Annual Component');
    pm.selectAxis(3);
    pm.plot(tYears,noiseComponent);
    pm.plot(tYears,x);
    pm.xlim([tYears(1),tYears(end)]);
    pm.legend({'Noise','Original'},'Location','eastoutside');
    pm.ylabel('EVI');
    pm.xlabel('t (years)');
    pm.title('Sub-seasonal / Noise Component');
    pm.format();
    pm.save(fullfile(savepath,'emd_scale_decomposition.png'));
end
