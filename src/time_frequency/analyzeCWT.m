function analyzeCWT(dataFile,fontName)
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
    Ts = double(S.Ts);

    tDate = datetime(1970,1,1) + days(t);
    tYears = year(tDate) + (day(tDate,'dayofyear') - 1) ./ 365;
    
    pm = PlotManager();
    pm.createFigure('size',[2,1],'font',fontName);
    pm.plot(tYears,x);
    pm.xlim([min(tYears),max(tYears)]);
    pm.xlabel('t (years)');
    pm.ylabel('x(t)');
    pm.format();
    pm.save(fullfile(savepath,'cwt_signal.png'));

    % --- Analysis ---
    wname = 'amor'; % Wavelet type
    numVoices = 32; % Number of voices per octave

    [wt,f,coi] = cwt(x,wname,1 / Ts,'VoicesPerOctave',numVoices);
    
    period = 1 ./ f;    % Convert frequency to period (days)
    power = abs(wt).^2; % Scalogram

    pm = PlotManager();
    pm.createFigure('hold','on','box','on','font',fontName);
    pm.imagesc(tYears,log2(period),pow2db(power + eps));
    pm.colormap(plasma(256));
    pm.colorbar('Label','Power (dB)');
    pm.xlabel('t (years)');
    pm.ylabel('Period (days)');
    pm.title('CWT Scalogram');
    periodTicks = 2.^(round(log2(min(period))):round(log2(max(period))));
    pm.yticks(log2(periodTicks));
    pm.yticklabels(arrayfun(@(p) sprintf('%d',round(p)),periodTicks,'UniformOutput',false));
    pm.xlim([min(tYears),max(tYears)]);
    pm.ylim([min(log2(period)),max(log2(period))]);
    pm.format();
    pm.save(fullfile(savepath,'cwt_scalogram.png'));

    % Energy
    scaleEnergy = zeros(length(f),1);
    for ii = 1:length(f)
        I = period(ii) <= coi;
        if any(I)
            scaleEnergy(ii) = sum(power(ii,I));
        else
            scaleEnergy(ii) = sum(power(ii,:));
        end
    end

    pm = PlotManager();
    pm.createFigure('size',[2,1],'font',fontName);
    pm.plot(log2(period),db(scaleEnergy),'k');
    pm.xlim([min(log2(period)),max(log2(period))]);
    pm.xlabel('Period (days)');
    pm.ylabel('Energy (dB)');
    pm.xticks(log2(periodTicks));
    pm.xticklabels(arrayfun(@(p) sprintf('%d',round(p)),periodTicks,'UniformOutput',false));
    pm.title('CWT Energy Spectrum');
    pm.save(fullfile(savepath,'cwt_energy.png'));

    % Scale-averaged power
    bands = struct(...
        'name',{'Sub-seasonal','Annual','Inter-annual'},...
        'limits',{[16 90],[180 540],[540 3650]});

    pm = PlotManager();
    pm.createFigure('size',[length(bands),1],'font',fontName);
    for ii = 1:length(bands)
        I = period >= P1 & period <= P2;
        s = period(I);
        weights = 1 ./ s;
        bandPower = weights' * abs(wt(I,:)).^2;

        pm.selectAxis(ii);
        pm.plot(tYears,pow2db(bandPower),'k');
        pm.xlim([min(tYears),max(tYears)]);
        pm.ylabel('Power (dB)');
        pm.title(sprintf('%s (%d–%d days)',bands(ii).name,bands(ii).limits(1),bands(ii).limits(2)));
    end
    pm.xlabel('t (years)');
    pm.save(fullfile(savepath,'cwt_scale_averaged_power.png'));

    % Annual scale
    [~,annualInd] = min(abs(period - 365));
    instPower = abs(wt(annualInd,:));
    instPhase = angle(wt(annualInd,:));
    instFreq = diff(unwrap(instPhase)) / (2 * pi * Ts);

    pm = PlotManager();
    pm.createFigure('size',[3,1],'font',fontName);
    pm.selectAxis(1);
    pm.plot(tYears,instPower,'k');
    pm.xlim([min(tYears),max(tYears)]);
    pm.ylabel('Amplitude');
    pm.selectAxis(2);
    pm.plot(tYears,instPhase,'k');
    pm.xlim([min(tYears),max(tYears)]);
    pm.ylabel('Phase');
    pm.selectAxis(3);
    pm.plot(tYears(2:end),instFreq,'k');
    pm.xlim([min(tYears),max(tYears)]);
    pm.ylabel('Frequency');
    pm.xlabel('t (years)');
    pm.sgtitle(sprintf('Period = %d days',round(period(annualInd))));
    pm.save(fullfile(savepath,'cwt_annual_scale.png'));

    % All scales
    [~,annualInd] = min(abs(period - 365));
    
    pm = PlotManager();
    pm.createFigure('size',[3,3],'font',fontName);
    S = [0.5,1,4];
    for ii = 1:length(S)
        [~,kk] = min(abs(period - S(ii) * period(annualInd)));

        instPower = pow2db(power(kk,:));
        instPhase = angle(wt(kk,:));
        instFreq = diff(unwrap(instPhase)) / (2 * pi * Ts) * 365;

        pm.selectAxis(sub2ind([3,3],ii,1));
        pm.plot(tYears,instPower,'k');
        pm.xlim([min(tYears),max(tYears)]);
        if ii == 1
            pm.ylabel('Power (dB)');
        end
        pm.title(sprintf('Period = %d Days',round(period(kk))));

        pm.selectAxis(sub2ind([3,3],ii,2));
        pm.plot(tYears,instPhase,'k');
        if ii == 1
            pm.ylabel('Phase (radians)');
        end
        pm.xlim([min(tYears),max(tYears)]);

        pm.selectAxis(sub2ind([3,3],ii,3));
        pm.plot(tYears(2:end),instFreq,'k');
        if ii == 1
            pm.ylabel('Frequency (cycles/year)');
        end
        pm.xlabel('t (years)');
        pm.xlim([min(tYears),max(tYears)]);
    end
    pm.save(fullfile(savepath,'cwt_multiple_scales.png'));
end
